"""Tests for ExtractPageContentTool.

This module contains tests for ExtractPageContentTool with mocked
TavilySearchService.
"""

from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from sgr_deep_research.core.models import ResearchContext, SourceData
from sgr_deep_research.core.tools.extract_page_content_tool import ExtractPageContentTool


class TestExtractPageContentTool:
    """Tests for ExtractPageContentTool class."""

    def test_extract_page_tool_creation(self):
        """Test creating ExtractPageContentTool with valid data."""
        tool = ExtractPageContentTool(
            reasoning="Need to extract content",
            urls=["https://example.com/1", "https://example.com/2"],
        )
        assert tool.reasoning == "Need to extract content"
        assert len(tool.urls) == 2
        assert tool.urls[0] == "https://example.com/1"

    def test_extract_page_tool_name(self):
        """Test that tool has correct name."""
        assert ExtractPageContentTool.tool_name == "extractpagecontenttool"

    def test_extract_page_tool_description(self):
        """Test that tool has a description."""
        assert ExtractPageContentTool.description is not None
        assert len(ExtractPageContentTool.description) > 0
        assert "extract" in ExtractPageContentTool.description.lower()

    def test_extract_page_tool_urls_validation_min(self):
        """Test urls validation - minimum 1 URL required."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractPageContentTool(
                reasoning="Test",
                urls=[],
            )
        assert "at least 1" in str(exc_info.value).lower()

    def test_extract_page_tool_urls_validation_max(self):
        """Test urls validation - maximum 5 URLs allowed."""
        with pytest.raises(ValidationError) as exc_info:
            ExtractPageContentTool(
                reasoning="Test",
                urls=["url1", "url2", "url3", "url4", "url5", "url6"],
            )
        assert "at most 5" in str(exc_info.value).lower()

    def test_extract_page_tool_urls_boundaries(self):
        """Test urls at valid boundaries."""
        tool_min = ExtractPageContentTool(reasoning="Test", urls=["https://example.com"])
        assert len(tool_min.urls) == 1

        tool_max = ExtractPageContentTool(
            reasoning="Test",
            urls=["url1", "url2", "url3", "url4", "url5"],
        )
        assert len(tool_max.urls) == 5

    def test_extract_page_tool_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            ExtractPageContentTool()

    @pytest.mark.asyncio
    async def test_extract_page_tool_execution_basic(self):
        """Test ExtractPageContentTool execution with mocked service."""
        tool = ExtractPageContentTool(
            reasoning="Extract content",
            urls=["https://example.com/page"],
        )

        # Mock the extract service
        mock_sources = [
            SourceData(
                number=0,
                title="page",
                url="https://example.com/page",
                full_content="Full page content here",
                char_count=22,
            ),
        ]
        tool._search_service.extract = AsyncMock(return_value=mock_sources)

        context = ResearchContext()
        result = await tool(context)

        # Verify extract was called
        tool._search_service.extract.assert_called_once_with(urls=["https://example.com/page"])

        # Verify result format
        assert "Extracted Page Content:" in result
        assert "Full page content here" in result
        assert "https://example.com/page" in result

    @pytest.mark.asyncio
    async def test_extract_page_tool_updates_existing_source(self):
        """Test that ExtractPageContentTool updates existing sources with full
        content."""
        tool = ExtractPageContentTool(
            reasoning="Extract",
            urls=["https://example.com/page"],
        )

        # Context already has this source from search
        context = ResearchContext()
        context.sources = {
            "https://example.com/page": SourceData(
                number=5,
                title="Original Title",
                url="https://example.com/page",
                snippet="Original snippet",
                full_content="",
                char_count=0,
            ),
        }

        # Mock extracted content
        mock_sources = [
            SourceData(
                number=999,  # This number should be ignored
                url="https://example.com/page",
                full_content="Extracted full content",
                char_count=22,
            ),
        ]
        tool._search_service.extract = AsyncMock(return_value=mock_sources)

        await tool(context)

        # Verify existing source was updated
        source = context.sources["https://example.com/page"]
        assert source.number == 5  # Original number preserved
        assert source.title == "Original Title"  # Original title preserved
        assert source.full_content == "Extracted full content"  # Updated
        assert source.char_count == 22  # Updated

    @pytest.mark.asyncio
    async def test_extract_page_tool_adds_new_source(self):
        """Test that ExtractPageContentTool adds new sources if URL not in
        context."""
        tool = ExtractPageContentTool(
            reasoning="Extract",
            urls=["https://example.com/new"],
        )

        # Context has 3 existing sources
        context = ResearchContext()
        context.sources = {
            "https://example.com/1": SourceData(number=1, url="https://example.com/1"),
            "https://example.com/2": SourceData(number=2, url="https://example.com/2"),
            "https://example.com/3": SourceData(number=3, url="https://example.com/3"),
        }

        mock_sources = [
            SourceData(
                number=0,
                url="https://example.com/new",
                full_content="New content",
                char_count=11,
            ),
        ]
        tool._search_service.extract = AsyncMock(return_value=mock_sources)

        await tool(context)

        # Verify new source was added with next number
        assert len(context.sources) == 4
        assert "https://example.com/new" in context.sources
        assert context.sources["https://example.com/new"].number == 4

    @pytest.mark.asyncio
    async def test_extract_page_tool_multiple_urls(self):
        """Test ExtractPageContentTool with multiple URLs."""
        tool = ExtractPageContentTool(
            reasoning="Extract multiple",
            urls=["https://example.com/1", "https://example.com/2"],
        )

        mock_sources = [
            SourceData(number=0, url="https://example.com/1", full_content="Content 1", char_count=9),
            SourceData(number=1, url="https://example.com/2", full_content="Content 2", char_count=9),
        ]
        tool._search_service.extract = AsyncMock(return_value=mock_sources)

        context = ResearchContext()
        result = await tool(context)

        # Verify both sources added
        assert len(context.sources) == 2
        assert "https://example.com/1" in context.sources
        assert "https://example.com/2" in context.sources

        # Verify both in result
        assert "Content 1" in result
        assert "Content 2" in result

    @pytest.mark.asyncio
    async def test_extract_page_tool_content_limit(self):
        """Test that ExtractPageContentTool respects content limit from
        config."""
        with patch("sgr_deep_research.core.tools.extract_page_content_tool.config") as mock_config:
            mock_config.scraping.content_limit = 50

            tool = ExtractPageContentTool(
                reasoning="Extract",
                urls=["https://example.com"],
            )

            long_content = "A" * 200  # 200 characters
            mock_sources = [
                SourceData(
                    number=0,
                    url="https://example.com",
                    full_content=long_content,
                    char_count=200,
                ),
            ]
            tool._search_service.extract = AsyncMock(return_value=mock_sources)

            context = ResearchContext()
            result = await tool(context)

            # Result should only show first 50 characters
            assert "A" * 50 in result
            assert "A" * 51 not in result
            assert "Content length: 50 characters" in result

    @pytest.mark.asyncio
    async def test_extract_page_tool_failed_extraction(self):
        """Test ExtractPageContentTool when extraction fails for a URL."""
        tool = ExtractPageContentTool(
            reasoning="Extract",
            urls=["https://example.com/failed"],
        )

        # Mock a source without full_content (failed extraction)
        mock_sources = [
            SourceData(
                number=0,
                url="https://example.com/failed",
                full_content="",
                char_count=0,
            ),
        ]
        tool._search_service.extract = AsyncMock(return_value=mock_sources)

        # Add the URL to context first
        context = ResearchContext()
        context.sources = {
            "https://example.com/failed": SourceData(
                number=1,
                url="https://example.com/failed",
            ),
        }

        result = await tool(context)

        # Should indicate failure
        assert "Failed to extract content" in result

    @pytest.mark.asyncio
    async def test_extract_page_tool_preserves_source_order(self):
        """Test that ExtractPageContentTool preserves source numbering."""
        tool = ExtractPageContentTool(
            reasoning="Extract",
            urls=["https://example.com/2", "https://example.com/5"],
        )

        # Context has sources with specific numbers
        context = ResearchContext()
        for i in range(1, 11):
            context.sources[f"https://example.com/{i}"] = SourceData(
                number=i,
                url=f"https://example.com/{i}",
            )

        mock_sources = [
            SourceData(number=0, url="https://example.com/2", full_content="Content 2", char_count=9),
            SourceData(number=1, url="https://example.com/5", full_content="Content 5", char_count=9),
        ]
        tool._search_service.extract = AsyncMock(return_value=mock_sources)

        await tool(context)

        # Verify numbers are preserved
        assert context.sources["https://example.com/2"].number == 2
        assert context.sources["https://example.com/5"].number == 5

    @pytest.mark.asyncio
    async def test_extract_page_tool_empty_result(self):
        """Test ExtractPageContentTool with no extracted sources."""
        tool = ExtractPageContentTool(
            reasoning="Extract",
            urls=["https://example.com"],
        )

        tool._search_service.extract = AsyncMock(return_value=[])

        context = ResearchContext()
        result = await tool(context)

        # Should still return formatted result
        assert "Extracted Page Content:" in result

    @pytest.mark.asyncio
    async def test_extract_page_tool_mixed_update_and_new(self):
        """Test ExtractPageContentTool with mix of existing and new URLs."""
        tool = ExtractPageContentTool(
            reasoning="Extract",
            urls=["https://example.com/existing", "https://example.com/new"],
        )

        # Context has one existing source
        context = ResearchContext()
        context.sources = {
            "https://example.com/existing": SourceData(
                number=1,
                url="https://example.com/existing",
                snippet="Existing snippet",
            ),
        }

        mock_sources = [
            SourceData(
                number=0,
                url="https://example.com/existing",
                full_content="Updated content",
                char_count=15,
            ),
            SourceData(
                number=1,
                url="https://example.com/new",
                full_content="New content",
                char_count=11,
            ),
        ]
        tool._search_service.extract = AsyncMock(return_value=mock_sources)

        await tool(context)

        # Verify existing updated, new added
        assert len(context.sources) == 2
        assert context.sources["https://example.com/existing"].number == 1
        assert context.sources["https://example.com/existing"].full_content == "Updated content"
        assert context.sources["https://example.com/new"].number == 2
