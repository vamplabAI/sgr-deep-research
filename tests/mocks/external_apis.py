"""Mock infrastructure for external APIs used in SGR Deep Research testing.

This module provides mock implementations for OpenAI, Tavily, and other external
services to enable testing without API costs or external dependencies.
"""

import asyncio
import json
import random
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest


class MockOpenAIResponse:
    """Mock response from OpenAI API for chat completions."""

    def __init__(self, content: str, model: str = "gpt-4o-mini", usage: Optional[Dict] = None):
        self.content = content
        self.model = model
        self.usage = usage or {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300}
        self.created = int(datetime.now().timestamp())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": f"chatcmpl-{random.randint(10000, 99999)}",
            "object": "chat.completion",
            "created": self.created,
            "model": self.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": self.content
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": self.usage
        }


class MockTavilySearchResult:
    """Mock search result from Tavily API."""

    def __init__(self, query: str, num_results: int = 5):
        self.query = query
        self.num_results = num_results

    def to_dict(self) -> Dict[str, Any]:
        """Generate realistic mock search results."""
        results = []
        for i in range(self.num_results):
            results.append({
                "title": f"Research Result {i+1} for {self.query}",
                "url": f"https://example{i+1}.com/article-{i+1}",
                "content": f"This is mock content for {self.query} from source {i+1}. " * 10,
                "score": round(0.9 - i * 0.1, 2),
                "published_date": "2024-01-15"
            })

        return {
            "query": self.query,
            "follow_up_questions": None,
            "answer": f"Based on the search results for '{self.query}', here are the key findings...",
            "images": [],
            "results": results,
            "response_time": round(random.uniform(0.5, 2.0), 2)
        }


class MockExternalAPIs:
    """Central mock manager for all external API interactions."""

    def __init__(self):
        self.openai_calls = []
        self.tavily_calls = []
        self.response_delay = 0.1  # Simulate network delay

    async def mock_openai_chat_completion(self, messages: List[Dict], **kwargs) -> MockOpenAIResponse:
        """Mock OpenAI chat completion with realistic response."""
        # Record the call for testing verification
        self.openai_calls.append({
            "messages": messages,
            "kwargs": kwargs,
            "timestamp": datetime.now()
        })

        # Simulate network delay
        await asyncio.sleep(self.response_delay)

        # Generate response based on the last user message
        last_message = messages[-1]["content"] if messages else "No input"

        # Different responses for different types of queries
        if "error" in last_message.lower():
            raise Exception("Mock API error for testing")
        elif "research" in last_message.lower():
            content = self._generate_research_response(last_message)
        elif "json" in last_message.lower() or "schema" in last_message.lower():
            content = self._generate_structured_response(last_message)
        else:
            content = f"Mock response for: {last_message}"

        return MockOpenAIResponse(content, kwargs.get("model", "gpt-4o-mini"))

    async def mock_tavily_search(self, query: str, **kwargs) -> MockTavilySearchResult:
        """Mock Tavily search with realistic results."""
        # Record the call for testing verification
        self.tavily_calls.append({
            "query": query,
            "kwargs": kwargs,
            "timestamp": datetime.now()
        })

        # Simulate network delay
        await asyncio.sleep(self.response_delay)

        # Simulate error conditions for testing
        if "error" in query.lower():
            raise Exception("Mock search API error for testing")

        num_results = kwargs.get("max_results", 5)
        return MockTavilySearchResult(query, num_results)

    def _generate_research_response(self, query: str) -> str:
        """Generate realistic research response for testing."""
        return f"""# Research Analysis: {query}

## Executive Summary
Based on comprehensive analysis of available sources, the following key findings emerge:

## Key Findings
1. **Primary Insight**: Mock finding 1 related to {query}
2. **Secondary Analysis**: Mock finding 2 with supporting evidence
3. **Future Implications**: Mock finding 3 projecting trends

## Methodology
This analysis incorporates data from multiple sources including academic papers,
industry reports, and expert interviews conducted between 2023-2024.

## Sources
1. [Mock Source 1](https://example1.com) - Academic Research Paper
2. [Mock Source 2](https://example2.com) - Industry Report
3. [Mock Source 3](https://example3.com) - Expert Analysis

## Conclusion
The research indicates significant developments in {query} with implications
for future planning and strategic decision-making.
"""

    def _generate_structured_response(self, query: str) -> str:
        """Generate structured JSON response for schema-guided reasoning."""
        return json.dumps({
            "reasoning": f"Analyzing query: {query}",
            "action": "search",
            "parameters": {
                "query": query,
                "max_results": 5
            },
            "confidence": 0.85,
            "next_steps": ["Execute search", "Analyze results", "Generate report"]
        })

    def reset_call_history(self):
        """Reset call history for clean test states."""
        self.openai_calls.clear()
        self.tavily_calls.clear()

    def get_call_stats(self) -> Dict[str, int]:
        """Get statistics about API calls for testing verification."""
        return {
            "openai_calls": len(self.openai_calls),
            "tavily_calls": len(self.tavily_calls),
            "total_calls": len(self.openai_calls) + len(self.tavily_calls)
        }


# Global mock instance for use across tests
mock_apis = MockExternalAPIs()


class MockHTTPClient:
    """Mock HTTP client for testing external API interactions."""

    def __init__(self, fail_rate: float = 0.0):
        self.fail_rate = fail_rate
        self.requests = []

    async def post(self, url: str, **kwargs) -> httpx.Response:
        """Mock HTTP POST request."""
        self.requests.append({"method": "POST", "url": url, "kwargs": kwargs})

        # Simulate random failures for resilience testing
        if random.random() < self.fail_rate:
            raise httpx.TimeoutException("Mock timeout error")

        # Simulate response based on URL
        if "openai" in url:
            return self._mock_openai_response(kwargs)
        elif "tavily" in url:
            return self._mock_tavily_response(kwargs)
        else:
            return self._mock_generic_response()

    def _mock_openai_response(self, kwargs: Dict) -> httpx.Response:
        """Mock OpenAI API response."""
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = MockOpenAIResponse("Mock response").to_dict()
        return response

    def _mock_tavily_response(self, kwargs: Dict) -> httpx.Response:
        """Mock Tavily API response."""
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = MockTavilySearchResult("mock query").to_dict()
        return response

    def _mock_generic_response(self) -> httpx.Response:
        """Mock generic HTTP response."""
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"status": "success", "data": "mock"}
        return response


# Pytest fixtures for easy test setup
@pytest.fixture
def mock_external_apis():
    """Fixture providing mock external APIs with clean state."""
    mock_apis.reset_call_history()
    return mock_apis


@pytest.fixture
def mock_http_client():
    """Fixture providing mock HTTP client."""
    return MockHTTPClient()


@pytest.fixture
def mock_openai_client():
    """Fixture providing mock OpenAI client."""
    client = AsyncMock()
    client.chat.completions.create = mock_apis.mock_openai_chat_completion
    return client


@pytest.fixture
def mock_tavily_client():
    """Fixture providing mock Tavily client."""
    client = AsyncMock()
    client.search = mock_apis.mock_tavily_search
    return client


# Helper functions for test assertions
def assert_openai_called(num_calls: int = None):
    """Assert that OpenAI API was called the expected number of times."""
    if num_calls is not None:
        assert len(mock_apis.openai_calls) == num_calls
    else:
        assert len(mock_apis.openai_calls) > 0


def assert_tavily_called(num_calls: int = None):
    """Assert that Tavily API was called the expected number of times."""
    if num_calls is not None:
        assert len(mock_apis.tavily_calls) == num_calls
    else:
        assert len(mock_apis.tavily_calls) > 0


def get_last_openai_call() -> Dict:
    """Get the most recent OpenAI API call for assertion."""
    assert mock_apis.openai_calls, "No OpenAI calls recorded"
    return mock_apis.openai_calls[-1]


def get_last_tavily_call() -> Dict:
    """Get the most recent Tavily API call for assertion."""
    assert mock_apis.tavily_calls, "No Tavily calls recorded"
    return mock_apis.tavily_calls[-1]