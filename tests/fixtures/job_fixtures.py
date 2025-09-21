"""Pytest fixtures for job testing in SGR Deep Research.

This module provides reusable fixtures for testing job management functionality,
including job creation, status tracking, and result validation.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def sample_job_request() -> Dict[str, Any]:
    """Fixture providing a basic job request for testing."""
    return {
        "query": "Analyze recent developments in quantum computing",
        "agent_type": "sgr-tools",
        "deep_level": 0,
        "priority": 0,
        "tags": ["quantum", "computing"],
        "metadata": {"test": True, "department": "research"}
    }


@pytest.fixture
def deep_job_request() -> Dict[str, Any]:
    """Fixture providing a deep research job request for testing."""
    return {
        "query": "Comprehensive analysis of AI market trends in 2024",
        "agent_type": "sgr-tools",
        "deep_level": 2,
        "priority": 10,
        "tags": ["ai", "market", "trends", "2024"],
        "metadata": {
            "department": "research",
            "project": "q1-analysis",
            "priority_reason": "quarterly_report"
        }
    }


@pytest.fixture
def invalid_job_request() -> Dict[str, Any]:
    """Fixture providing an invalid job request for error testing."""
    return {
        "query": "",  # Empty query should fail validation
        "agent_type": "invalid-agent",  # Invalid agent type
        "deep_level": 15,  # Beyond allowed range
        "priority": 200,  # Beyond allowed range
        "tags": ["tag"] * 20,  # Too many tags
    }


@pytest.fixture
def sample_job_id() -> str:
    """Fixture providing a consistent job ID for testing."""
    return "123e4567-e89b-12d3-a456-426614174000"


@pytest.fixture
def pending_job_status(sample_job_id: str) -> Dict[str, Any]:
    """Fixture providing a pending job status for testing."""
    return {
        "job_id": sample_job_id,
        "status": "pending",
        "progress": 0.0,
        "current_step": "",
        "steps_completed": 0,
        "total_steps": 20,
        "searches_used": 0,
        "sources_found": 0,
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "completed_at": None,
        "estimated_completion": (datetime.now() + timedelta(minutes=10)).isoformat()
    }


@pytest.fixture
def running_job_status(sample_job_id: str) -> Dict[str, Any]:
    """Fixture providing a running job status for testing."""
    started_time = datetime.now() - timedelta(minutes=5)
    return {
        "job_id": sample_job_id,
        "status": "running",
        "progress": 45.5,
        "current_step": "Analyzing research sources",
        "steps_completed": 9,
        "total_steps": 20,
        "searches_used": 3,
        "sources_found": 8,
        "created_at": (started_time - timedelta(seconds=30)).isoformat(),
        "started_at": started_time.isoformat(),
        "completed_at": None,
        "estimated_completion": (datetime.now() + timedelta(minutes=5)).isoformat()
    }


@pytest.fixture
def completed_job_status(sample_job_id: str) -> Dict[str, Any]:
    """Fixture providing a completed job status for testing."""
    created_time = datetime.now() - timedelta(minutes=15)
    started_time = created_time + timedelta(seconds=30)
    completed_time = datetime.now()

    return {
        "job_id": sample_job_id,
        "status": "completed",
        "progress": 100.0,
        "current_step": "Research completed",
        "steps_completed": 20,
        "total_steps": 20,
        "searches_used": 5,
        "sources_found": 12,
        "created_at": created_time.isoformat(),
        "started_at": started_time.isoformat(),
        "completed_at": completed_time.isoformat(),
        "estimated_completion": None
    }


@pytest.fixture
def failed_job_status(sample_job_id: str) -> Dict[str, Any]:
    """Fixture providing a failed job status for testing."""
    created_time = datetime.now() - timedelta(minutes=10)
    started_time = created_time + timedelta(seconds=30)
    failed_time = started_time + timedelta(minutes=5)

    return {
        "job_id": sample_job_id,
        "status": "failed",
        "progress": 25.0,
        "current_step": "Search operation failed",
        "steps_completed": 5,
        "total_steps": 20,
        "searches_used": 2,
        "sources_found": 3,
        "created_at": created_time.isoformat(),
        "started_at": started_time.isoformat(),
        "completed_at": failed_time.isoformat(),
        "estimated_completion": None
    }


@pytest.fixture
def sample_job_result() -> Dict[str, Any]:
    """Fixture providing a complete job result for testing."""
    return {
        "final_answer": """# Quantum Computing Analysis

## Executive Summary
Recent developments in quantum computing show significant progress in both hardware and software domains.

## Key Findings
1. **Hardware Advances**: New superconducting qubits achieving 99.9% fidelity
2. **Software Stack**: Development of quantum programming languages and compilers
3. **Commercial Applications**: Early adoption in optimization and cryptography

## Technical Analysis
The field has seen breakthrough developments in error correction codes and quantum algorithms.
Several major technology companies have announced quantum supremacy demonstrations.

## Sources Used
- IBM Quantum Research Papers (2024)
- Google Quantum AI Publications
- Nature Quantum Information Journal
- IEEE Quantum Computing Conference Proceedings

## Conclusion
Quantum computing is transitioning from research to practical applications with significant
implications for computational science and industry.
""",
        "report_url": "/jobs/123e4567-e89b-12d3-a456-426614174000/report",
        "sources": [
            {
                "number": 1,
                "url": "https://research.ibm.com/quantum",
                "title": "IBM Quantum Computing Research",
                "content_excerpt": "Recent advances in superconducting quantum processors...",
                "confidence_score": 0.95
            },
            {
                "number": 2,
                "url": "https://ai.google/quantum",
                "title": "Google Quantum AI",
                "content_excerpt": "Quantum supremacy demonstrations using Sycamore processor...",
                "confidence_score": 0.92
            },
            {
                "number": 3,
                "url": "https://nature.com/quantum-information",
                "title": "Nature Quantum Information",
                "content_excerpt": "Error correction protocols for NISQ devices...",
                "confidence_score": 0.88
            }
        ],
        "metrics": {
            "total_duration_seconds": 892.5,
            "api_calls_made": 25,
            "tokens_consumed": 15000,
            "estimated_cost_usd": 2.45,
            "search_operations": 8
        },
        "artifacts": [
            {
                "file_path": "reports/job_123_report.md",
                "file_type": "text/markdown",
                "size_bytes": 25600,
                "description": "Full research report in Markdown format",
                "download_url": "/jobs/123e4567-e89b-12d3-a456-426614174000/files/report.md"
            }
        ]
    }


@pytest.fixture
def sample_job_error() -> Dict[str, Any]:
    """Fixture providing a job error for testing."""
    return {
        "error_type": "network",
        "error_message": "Failed to connect to external research API after 3 retries",
        "error_details": {
            "endpoint": "https://api.tavily.com/search",
            "status_code": 503,
            "retry_attempts": 3,
            "last_error": "Service temporarily unavailable"
        },
        "retry_count": 3,
        "is_retryable": True,
        "occurred_at": datetime.now().isoformat()
    }


@pytest.fixture
def job_list_response() -> Dict[str, Any]:
    """Fixture providing a job list response for testing."""
    return {
        "jobs": [
            {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "completed",
                "progress": 100.0,
                "query": "Analyze recent developments in quantum...",
                "agent_type": "sgr-tools",
                "tags": ["quantum", "computing"],
                "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
                "completed_at": (datetime.now() - timedelta(hours=1)).isoformat()
            },
            {
                "job_id": "456e7890-e12b-34c5-d678-901234567890",
                "status": "running",
                "progress": 65.0,
                "query": "Research AI market trends in 2024",
                "agent_type": "sgr-tools",
                "tags": ["ai", "market"],
                "created_at": (datetime.now() - timedelta(minutes=30)).isoformat(),
                "completed_at": None
            },
            {
                "job_id": "789a0123-b45c-67d8-e901-234567890123",
                "status": "pending",
                "progress": 0.0,
                "query": "Investigate blockchain technology advances",
                "agent_type": "sgr",
                "tags": ["blockchain"],
                "created_at": (datetime.now() - timedelta(minutes=5)).isoformat(),
                "completed_at": None
            }
        ],
        "total": 3,
        "limit": 20,
        "offset": 0
    }


@pytest.fixture
def sse_event_stream() -> List[str]:
    """Fixture providing SSE event stream data for testing."""
    return [
        "event: job_progress\ndata: {\"job_id\": \"123e4567-e89b-12d3-a456-426614174000\", \"progress\": 25.0, \"current_step\": \"Starting research\"}\n\n",
        "event: job_progress\ndata: {\"job_id\": \"123e4567-e89b-12d3-a456-426614174000\", \"progress\": 50.0, \"current_step\": \"Analyzing sources\"}\n\n",
        "event: job_progress\ndata: {\"job_id\": \"123e4567-e89b-12d3-a456-426614174000\", \"progress\": 75.0, \"current_step\": \"Generating report\"}\n\n",
        "event: job_complete\ndata: {\"job_id\": \"123e4567-e89b-12d3-a456-426614174000\", \"status\": \"completed\"}\n\n"
    ]


@pytest.fixture
def mock_job_queue():
    """Fixture providing a mock job queue for testing."""
    queue = MagicMock()
    queue.submit_job = AsyncMock(return_value="123e4567-e89b-12d3-a456-426614174000")
    queue.get_job_status = AsyncMock()
    queue.cancel_job = AsyncMock(return_value=True)
    queue.list_jobs = AsyncMock()
    return queue


@pytest.fixture
def mock_job_executor():
    """Fixture providing a mock job executor for testing."""
    executor = MagicMock()
    executor.execute_job = AsyncMock()
    executor.cancel_job = AsyncMock(return_value=True)
    executor.get_job_progress = AsyncMock(return_value=50.0)
    return executor


@pytest.fixture
def mock_job_storage():
    """Fixture providing a mock job storage for testing."""
    storage = MagicMock()
    storage.save_job = AsyncMock()
    storage.get_job = AsyncMock()
    storage.update_job = AsyncMock()
    storage.delete_job = AsyncMock()
    storage.list_jobs = AsyncMock()
    return storage


@pytest.fixture
def test_client():
    """Fixture providing a FastAPI test client for API testing."""
    from fastapi.testclient import TestClient
    # Note: This will be updated once we have the actual FastAPI app
    # For now, returning a mock client
    return MagicMock(spec=TestClient)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Utility fixtures for creating test data
@pytest.fixture
def job_factory():
    """Factory fixture for creating job test data."""
    def _create_job(**kwargs):
        defaults = {
            "job_id": str(uuid.uuid4()),
            "query": "Test research query",
            "agent_type": "sgr-tools",
            "deep_level": 0,
            "priority": 0,
            "tags": ["test"],
            "metadata": {"test": True},
            "status": "pending",
            "progress": 0.0,
            "created_at": datetime.now().isoformat()
        }
        defaults.update(kwargs)
        return defaults
    return _create_job


@pytest.fixture
def multiple_jobs(job_factory):
    """Fixture providing multiple jobs for list testing."""
    return [
        job_factory(status="completed", progress=100.0, tags=["ai", "research"]),
        job_factory(status="running", progress=45.0, tags=["quantum"]),
        job_factory(status="pending", progress=0.0, tags=["blockchain"]),
        job_factory(status="failed", progress=25.0, tags=["energy"]),
        job_factory(status="cancelled", progress=15.0, tags=["finance"])
    ]


# Parametrized fixtures for comprehensive testing
@pytest.fixture(params=["sgr", "sgr-tools", "sgr-auto-tools", "sgr-so-tools", "tools"])
def agent_type(request):
    """Parametrized fixture for testing all agent types."""
    return request.param


@pytest.fixture(params=[0, 1, 2, 3, 4])
def deep_level(request):
    """Parametrized fixture for testing all deep levels."""
    return request.param


@pytest.fixture(params=["pending", "running", "completed", "failed", "cancelled"])
def job_status(request):
    """Parametrized fixture for testing all job statuses."""
    return request.param