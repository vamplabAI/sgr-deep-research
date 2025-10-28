"""Tests for WebSearchTool.

This module contains tests for WebSearchTool with mocked TavilySearchService.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from sgr_deep_research.core.models import ResearchContext, SearchResult, SourceData
from sgr_deep_research.core.tools.web_search_tool import WebSearchTool


class TestWebSearchTool:
    """Tests for WebSearchTool class."""

    def test_web_search_tool_creation(self):
        """Test creating WebSearchTool with valid data."""
        tool = WebSearchTool(
            reasoning="Need to search for information",
            query="test query",
            max_results=5,
        )
        assert tool.reasoning == "Need to search for information"
        assert tool.query == "test query"
        assert tool.max_results == 5

    def test_web_search_tool_name(self):
        """Test that tool has correct name."""
        assert WebSearchTool.tool_name == "websearchtool"

    def test_web_search_tool_description(self):
        """Test that tool has a description."""
        assert WebSearchTool.description is not None
        assert len(WebSearchTool.description) > 0
        assert "search" in WebSearchTool.description.lower()

    def test_web_search_tool_default_max_results(self):
        """Test default max_results value."""
        with patch("sgr_deep_research.core.tools.web_search_tool.config") as mock_config:
            mock_config.search.max_results = 10
            
            tool = WebSearchTool(
                reasoning="Test",
                query="test query",
            )
            assert tool.max_results == 10

    def test_web_search_tool_max_results_validation_min(self):
        """Test max_results validation - minimum value."""
        with pytest.raises(ValidationError) as exc_info:
            WebSearchTool(
                reasoning="Test",
                query="test",
                max_results=0,
            )
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_web_search_tool_max_results_validation_max(self):
        """Test max_results validation - maximum value."""
        with pytest.raises(ValidationError) as exc_info:
            WebSearchTool(
                reasoning="Test",
                query="test",
                max_results=11,
            )
        assert "less than or equal to 10" in str(exc_info.value)

    def test_web_search_tool_max_results_boundaries(self):
        """Test max_results at valid boundaries."""
        tool_min = WebSearchTool(reasoning="Test", query="test", max_results=1)
        assert tool_min.max_results == 1

        tool_max = WebSearchTool(reasoning="Test", query="test", max_results=10)
        assert tool_max.max_results == 10

    def test_web_search_tool_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            WebSearchTool()

    @pytest.mark.asyncio
    async def test_web_search_tool_execution_basic(self):
        """Test WebSearchTool execution with mocked service."""
        tool = WebSearchTool(
            reasoning="Test search",
            query="test query",
            max_results=3,
        )
        
        # Mock the search service
        mock_sources = [
            SourceData(
                number=1,
                title="Result 1",
                url="https://example.com/1",
                snippet="Snippet 1",
            ),
            SourceData(
                number=2,
                title="Result 2",
                url="https://example.com/2",
                snippet="Snippet 2",
            ),
        ]
        
        tool._search_service.search = AsyncMock(return_value=mock_sources)
        
        context = ResearchContext()
        result = await tool(context)
        
        # Verify search was called with correct parameters
        tool._search_service.search.assert_called_once_with(
            query="test query",
            max_results=3,
            include_raw_content=False,
        )
        
        # Verify result format
        assert "Search Query: test query" in result
        assert "Result 1" in result
        assert "Result 2" in result
        assert "https://example.com/1" in result

    @pytest.mark.asyncio
    async def test_web_search_tool_updates_context_sources(self):
        """Test that WebSearchTool updates context sources."""
        tool = WebSearchTool(
            reasoning="Test",
            query="test",
            max_results=2,
        )
        
        mock_sources = [
            SourceData(number=1, title="Test", url="https://example.com/1", snippet="Snippet"),
        ]
        tool._search_service.search = AsyncMock(return_value=mock_sources)
        
        context = ResearchContext()
        await tool(context)
        
        # Verify sources were added to context
        assert len(context.sources) == 1
        assert "https://example.com/1" in context.sources
        assert context.sources["https://example.com/1"].title == "Test"

    @pytest.mark.asyncio
    async def test_web_search_tool_updates_context_searches(self):
        """Test that WebSearchTool updates context searches list."""
        tool = WebSearchTool(
            reasoning="Test",
            query="test query",
            max_results=2,
        )
        
        mock_sources = [
            SourceData(number=1, url="https://example.com/1", snippet="Snippet"),
        ]
        tool._search_service.search = AsyncMock(return_value=mock_sources)
        
        context = ResearchContext()
        assert len(context.searches) == 0
        
        await tool(context)
        
        # Verify searches were updated
        assert len(context.searches) == 1
        assert isinstance(context.searches[0], SearchResult)
        assert context.searches[0].query == "test query"
        assert len(context.searches[0].citations) == 1

    @pytest.mark.asyncio
    async def test_web_search_tool_increments_searches_used(self):
        """Test that WebSearchTool increments searches_used counter."""
        tool = WebSearchTool(
            reasoning="Test",
            query="test",
            max_results=1,
        )
        
        tool._search_service.search = AsyncMock(return_value=[])
        
        context = ResearchContext()
        assert context.searches_used == 0
        
        await tool(context)
        
        assert context.searches_used == 1

    @pytest.mark.asyncio
    async def test_web_search_tool_rearranges_source_numbers(self):
        """Test that WebSearchTool rearranges source numbers based on existing sources."""
        tool = WebSearchTool(
            reasoning="Test",
            query="test",
            max_results=2,
        )
        
        # Mock sources that will be returned
        mock_sources = [
            SourceData(number=99, url="https://example.com/new1", snippet="New 1"),
            SourceData(number=100, url="https://example.com/new2", snippet="New 2"),
        ]
        tool._search_service.search = AsyncMock(return_value=mock_sources)
        
        # Context already has 3 sources
        context = ResearchContext()
        context.sources = {
            "https://example.com/old1": SourceData(number=1, url="https://example.com/old1"),
            "https://example.com/old2": SourceData(number=2, url="https://example.com/old2"),
            "https://example.com/old3": SourceData(number=3, url="https://example.com/old3"),
        }
        
        await tool(context)
        
        # New sources should be numbered 4 and 5
        assert context.sources["https://example.com/new1"].number == 4
        assert context.sources["https://example.com/new2"].number == 5

    @pytest.mark.asyncio
    async def test_web_search_tool_snippet_truncation(self):
        """Test that long snippets are truncated in output."""
        tool = WebSearchTool(
            reasoning="Test",
            query="test",
            max_results=1,
        )
        
        long_snippet = "A" * 150  # 150 characters
        mock_sources = [
            SourceData(
                number=1,
                url="https://example.com",
                snippet=long_snippet,
            ),
        ]
        tool._search_service.search = AsyncMock(return_value=mock_sources)
        
        context = ResearchContext()
        result = await tool(context)
        
        # Snippet should be truncated to 100 chars + "..."
        assert "A" * 100 in result
        assert "..." in result
        # Full snippet should not be in result
        assert "A" * 150 not in result

    @pytest.mark.asyncio
    async def test_web_search_tool_empty_results(self):
        """Test WebSearchTool with no search results."""
        tool = WebSearchTool(
            reasoning="Test",
            query="test",
            max_results=5,
        )
        
        tool._search_service.search = AsyncMock(return_value=[])
        
        context = ResearchContext()
        result = await tool(context)
        
        # Should still return formatted result
        assert "Search Query: test" in result
        assert "Search Results" in result
        # Context should still be updated
        assert len(context.searches) == 1
        assert context.searches_used == 1

    @pytest.mark.asyncio
    async def test_web_search_tool_multiple_executions(self):
        """Test multiple executions of WebSearchTool."""
        tool1 = WebSearchTool(reasoning="First", query="query 1", max_results=1)
        tool2 = WebSearchTool(reasoning="Second", query="query 2", max_results=1)
        
        mock_sources_1 = [SourceData(number=1, url="https://example.com/1", snippet="S1")]
        mock_sources_2 = [SourceData(number=2, url="https://example.com/2", snippet="S2")]
        
        tool1._search_service.search = AsyncMock(return_value=mock_sources_1)
        tool2._search_service.search = AsyncMock(return_value=mock_sources_2)
        
        context = ResearchContext()
        
        await tool1(context)
        assert len(context.searches) == 1
        assert context.searches_used == 1
        
        await tool2(context)
        assert len(context.searches) == 2
        assert context.searches_used == 2
        assert len(context.sources) == 2

    @pytest.mark.asyncio
    async def test_web_search_tool_timestamp_in_search_result(self):
        """Test that search results have timestamp."""
        tool = WebSearchTool(reasoning="Test", query="test", max_results=1)
        tool._search_service.search = AsyncMock(return_value=[])
        
        context = ResearchContext()
        before = datetime.now()
        await tool(context)
        after = datetime.now()
        
        assert len(context.searches) == 1
        assert before <= context.searches[0].timestamp <= after

