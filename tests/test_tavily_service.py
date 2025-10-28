"""Tests for Tavily Search Service.

This module contains tests for TavilySearchService with mocked API calls.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sgr_deep_research.core.models import SourceData
from sgr_deep_research.services.tavily_search import TavilySearchService


class TestTavilySearchService:
    """Tests for TavilySearchService class."""

    def test_tavily_service_initialization(self):
        """Test TavilySearchService initialization."""
        with patch("sgr_deep_research.services.tavily_search.get_config") as mock_config:
            mock_config.return_value.tavily.api_key = "test_key"
            mock_config.return_value.tavily.api_base_url = "https://api.tavily.com"
            
            service = TavilySearchService()
            assert service._config is not None
            assert service._client is not None

    def test_rearrange_sources_empty_list(self):
        """Test rearrange_sources with empty list."""
        sources = []
        result = TavilySearchService.rearrange_sources(sources)
        assert result == []

    def test_rearrange_sources_default_starting_number(self):
        """Test rearrange_sources with default starting number."""
        sources = [
            SourceData(number=10, url="https://example.com/1"),
            SourceData(number=20, url="https://example.com/2"),
            SourceData(number=30, url="https://example.com/3"),
        ]
        
        result = TavilySearchService.rearrange_sources(sources)
        
        assert len(result) == 3
        assert result[0].number == 1
        assert result[1].number == 2
        assert result[2].number == 3

    def test_rearrange_sources_custom_starting_number(self):
        """Test rearrange_sources with custom starting number."""
        sources = [
            SourceData(number=100, url="https://example.com/1"),
            SourceData(number=200, url="https://example.com/2"),
        ]
        
        result = TavilySearchService.rearrange_sources(sources, starting_number=5)
        
        assert len(result) == 2
        assert result[0].number == 5
        assert result[1].number == 6

    def test_rearrange_sources_preserves_other_fields(self):
        """Test that rearrange_sources preserves all other fields."""
        sources = [
            SourceData(
                number=999,
                title="Test Title",
                url="https://example.com",
                snippet="Test snippet",
                full_content="Full content here",
                char_count=100,
            )
        ]
        
        result = TavilySearchService.rearrange_sources(sources, starting_number=10)
        
        assert result[0].number == 10
        assert result[0].title == "Test Title"
        assert result[0].url == "https://example.com"
        assert result[0].snippet == "Test snippet"
        assert result[0].full_content == "Full content here"
        assert result[0].char_count == 100

    def test_convert_to_source_data_empty_response(self):
        """Test _convert_to_source_data with empty response."""
        service = TavilySearchService()
        response = {"results": []}
        
        result = service._convert_to_source_data(response)
        
        assert result == []

    def test_convert_to_source_data_basic(self):
        """Test _convert_to_source_data with basic response."""
        service = TavilySearchService()
        response = {
            "results": [
                {
                    "title": "Test Article",
                    "url": "https://example.com/article",
                    "content": "This is a test snippet",
                }
            ]
        }
        
        result = service._convert_to_source_data(response)
        
        assert len(result) == 1
        assert result[0].number == 0
        assert result[0].title == "Test Article"
        assert result[0].url == "https://example.com/article"
        assert result[0].snippet == "This is a test snippet"

    def test_convert_to_source_data_with_raw_content(self):
        """Test _convert_to_source_data with raw_content."""
        service = TavilySearchService()
        response = {
            "results": [
                {
                    "title": "Article",
                    "url": "https://example.com",
                    "content": "Snippet",
                    "raw_content": "Full raw content of the page",
                }
            ]
        }
        
        result = service._convert_to_source_data(response)
        
        assert len(result) == 1
        assert result[0].full_content == "Full raw content of the page"
        assert result[0].char_count == len("Full raw content of the page")

    def test_convert_to_source_data_skips_missing_url(self):
        """Test that _convert_to_source_data skips results without URL."""
        service = TavilySearchService()
        response = {
            "results": [
                {
                    "title": "Valid Article",
                    "url": "https://example.com",
                    "content": "Content",
                },
                {
                    "title": "Invalid Article",
                    "url": "",  # Empty URL
                    "content": "Content",
                },
                {
                    "title": "Another Invalid",
                    # Missing url key
                    "content": "Content",
                },
            ]
        }
        
        result = service._convert_to_source_data(response)
        
        # Should only include the valid one
        assert len(result) == 1
        assert result[0].title == "Valid Article"

    def test_convert_to_source_data_multiple_results(self):
        """Test _convert_to_source_data with multiple results."""
        service = TavilySearchService()
        response = {
            "results": [
                {"title": "First", "url": "https://example.com/1", "content": "Content 1"},
                {"title": "Second", "url": "https://example.com/2", "content": "Content 2"},
                {"title": "Third", "url": "https://example.com/3", "content": "Content 3"},
            ]
        }
        
        result = service._convert_to_source_data(response)
        
        assert len(result) == 3
        assert result[0].number == 0
        assert result[1].number == 1
        assert result[2].number == 2

    @pytest.mark.asyncio
    async def test_search_basic(self):
        """Test search method with mocked Tavily client."""
        with patch("sgr_deep_research.services.tavily_search.get_config") as mock_config:
            mock_config.return_value.tavily.api_key = "test_key"
            mock_config.return_value.tavily.api_base_url = "https://api.tavily.com"
            mock_config.return_value.search.max_results = 10
            
            service = TavilySearchService()
            
            # Mock the Tavily client search method
            mock_response = {
                "results": [
                    {
                        "title": "Search Result",
                        "url": "https://example.com",
                        "content": "Search snippet",
                    }
                ]
            }
            service._client.search = AsyncMock(return_value=mock_response)
            
            result = await service.search("test query")
            
            assert len(result) == 1
            assert result[0].title == "Search Result"
            assert result[0].url == "https://example.com"
            
            # Verify the client was called with correct parameters
            service._client.search.assert_called_once_with(
                query="test query",
                max_results=10,
                include_raw_content=True,
            )

    @pytest.mark.asyncio
    async def test_search_custom_max_results(self):
        """Test search with custom max_results parameter."""
        with patch("sgr_deep_research.services.tavily_search.get_config") as mock_config:
            mock_config.return_value.tavily.api_key = "test_key"
            mock_config.return_value.tavily.api_base_url = "https://api.tavily.com"
            mock_config.return_value.search.max_results = 10
            
            service = TavilySearchService()
            service._client.search = AsyncMock(return_value={"results": []})
            
            await service.search("test query", max_results=5)
            
            service._client.search.assert_called_once_with(
                query="test query",
                max_results=5,
                include_raw_content=True,
            )

    @pytest.mark.asyncio
    async def test_search_include_raw_content_false(self):
        """Test search with include_raw_content=False."""
        with patch("sgr_deep_research.services.tavily_search.get_config") as mock_config:
            mock_config.return_value.tavily.api_key = "test_key"
            mock_config.return_value.tavily.api_base_url = "https://api.tavily.com"
            mock_config.return_value.search.max_results = 10
            
            service = TavilySearchService()
            service._client.search = AsyncMock(return_value={"results": []})
            
            await service.search("test query", include_raw_content=False)
            
            service._client.search.assert_called_once_with(
                query="test query",
                max_results=10,
                include_raw_content=False,
            )

    @pytest.mark.asyncio
    async def test_extract_basic(self):
        """Test extract method with mocked Tavily client."""
        with patch("sgr_deep_research.services.tavily_search.get_config") as mock_config:
            mock_config.return_value.tavily.api_key = "test_key"
            mock_config.return_value.tavily.api_base_url = "https://api.tavily.com"
            
            service = TavilySearchService()
            
            # Mock the Tavily client extract method
            mock_response = {
                "results": [
                    {
                        "url": "https://example.com/page",
                        "raw_content": "Full page content extracted",
                    }
                ]
            }
            service._client.extract = AsyncMock(return_value=mock_response)
            
            urls = ["https://example.com/page"]
            result = await service.extract(urls)
            
            assert len(result) == 1
            assert result[0].url == "https://example.com/page"
            assert result[0].full_content == "Full page content extracted"
            assert result[0].char_count == len("Full page content extracted")
            
            # Verify the client was called
            service._client.extract.assert_called_once_with(urls=urls)

    @pytest.mark.asyncio
    async def test_extract_multiple_urls(self):
        """Test extract with multiple URLs."""
        with patch("sgr_deep_research.services.tavily_search.get_config") as mock_config:
            mock_config.return_value.tavily.api_key = "test_key"
            mock_config.return_value.tavily.api_base_url = "https://api.tavily.com"
            
            service = TavilySearchService()
            
            mock_response = {
                "results": [
                    {"url": "https://example.com/1", "raw_content": "Content 1"},
                    {"url": "https://example.com/2", "raw_content": "Content 2"},
                ]
            }
            service._client.extract = AsyncMock(return_value=mock_response)
            
            urls = ["https://example.com/1", "https://example.com/2"]
            result = await service.extract(urls)
            
            assert len(result) == 2
            assert result[0].url == "https://example.com/1"
            assert result[1].url == "https://example.com/2"

    @pytest.mark.asyncio
    async def test_extract_with_failed_results(self):
        """Test extract with some failed URLs."""
        with patch("sgr_deep_research.services.tavily_search.get_config") as mock_config:
            mock_config.return_value.tavily.api_key = "test_key"
            mock_config.return_value.tavily.api_base_url = "https://api.tavily.com"
            
            service = TavilySearchService()
            
            mock_response = {
                "results": [
                    {"url": "https://example.com/success", "raw_content": "Content"},
                ],
                "failed_results": [
                    {"url": "https://example.com/failed", "error": "Timeout"},
                ],
            }
            service._client.extract = AsyncMock(return_value=mock_response)
            
            urls = ["https://example.com/success", "https://example.com/failed"]
            result = await service.extract(urls)
            
            # Should only return successful extractions
            assert len(result) == 1
            assert result[0].url == "https://example.com/success"

    @pytest.mark.asyncio
    async def test_extract_skips_results_without_url(self):
        """Test that extract skips results without URL."""
        with patch("sgr_deep_research.services.tavily_search.get_config") as mock_config:
            mock_config.return_value.tavily.api_key = "test_key"
            mock_config.return_value.tavily.api_base_url = "https://api.tavily.com"
            
            service = TavilySearchService()
            
            mock_response = {
                "results": [
                    {"url": "https://example.com", "raw_content": "Valid"},
                    {"raw_content": "No URL"},  # Missing URL
                    {"url": "", "raw_content": "Empty URL"},  # Empty URL
                ]
            }
            service._client.extract = AsyncMock(return_value=mock_response)
            
            result = await service.extract(["https://example.com"])
            
            # Should only include the valid one
            assert len(result) == 1
            assert result[0].url == "https://example.com"

    @pytest.mark.asyncio
    async def test_extract_generates_title_from_url(self):
        """Test that extract generates title from URL when not provided."""
        with patch("sgr_deep_research.services.tavily_search.get_config") as mock_config:
            mock_config.return_value.tavily.api_key = "test_key"
            mock_config.return_value.tavily.api_base_url = "https://api.tavily.com"
            
            service = TavilySearchService()
            
            mock_response = {
                "results": [
                    {
                        "url": "https://example.com/article/test-page",
                        "raw_content": "Content",
                    }
                ]
            }
            service._client.extract = AsyncMock(return_value=mock_response)
            
            result = await service.extract(["https://example.com/article/test-page"])
            
            assert len(result) == 1
            # Title should be extracted from URL path
            assert result[0].title == "test-page"

