import logging

from tavily import AsyncTavilyClient

from sgr_deep_research.core.agent_config import GlobalConfig
from sgr_deep_research.core.models import SourceData

logger = logging.getLogger(__name__)


class TavilySearchService:
    def __init__(self):
        config = GlobalConfig()
        self._client = AsyncTavilyClient(
            api_key=config.search.tavily_api_key, api_base_url=config.search.tavily_api_base_url
        )
        self._config = config

    @staticmethod
    def rearrange_sources(sources: list[SourceData], starting_number=1) -> list[SourceData]:
        for i, source in enumerate(sources, starting_number):
            source.number = i
        return sources

    async def search(
        self,
        query: str,
        max_results: int | None = None,
        include_raw_content: bool = True,
    ) -> list[SourceData]:
        """Perform search through Tavily API and return results with
        SourceData.

        Args:
            query: Search query
            max_results: Maximum number of results (default from config)
            include_raw_content: Include raw page content

        Returns:
            Tuple with tavily answer and list of SourceData
        """
        max_results = max_results or self._config.search.max_results
        logger.info(f"🔍 Tavily search: '{query}' (max_results={max_results})")

        # Execute search through Tavily
        response = await self._client.search(
            query=query,
            max_results=max_results,
            include_raw_content=include_raw_content,
        )

        # Convert results to SourceData
        sources = self._convert_to_source_data(response)
        return sources

    async def extract(self, urls: list[str]) -> list[SourceData]:
        """Extract full content from specific URLs using Tavily Extract API.

        Args:
            urls: List of URLs to extract content from

        Returns:
            List of SourceData with extracted content
        """
        logger.info(f"📄 Tavily extract: {len(urls)} URLs")

        response = await self._client.extract(urls=urls)

        sources = []
        for i, result in enumerate(response.get("results", [])):
            if not result.get("url"):
                continue

            source = SourceData(
                number=i,
                title=result.get("url", "").split("/")[-1] or "Extracted Content",
                url=result.get("url", ""),
                snippet="",
                full_content=result.get("raw_content", ""),
                char_count=len(result.get("raw_content", "")),
            )
            sources.append(source)

        failed_urls = response.get("failed_results", [])
        if failed_urls:
            logger.warning(f"⚠️ Failed to extract {len(failed_urls)} URLs: {failed_urls}")

        return sources

    def _convert_to_source_data(self, response: dict) -> list[SourceData]:
        """Convert Tavily response to SourceData list."""
        sources = []

        for i, result in enumerate(response.get("results", [])):
            if not result.get("url", ""):
                continue

            source = SourceData(
                number=i,
                title=result.get("title", ""),
                url=result.get("url", ""),
                snippet=result.get("content", ""),
            )
            if result.get("raw_content", ""):
                source.full_content = result["raw_content"]
                source.char_count = len(source.full_content)
            sources.append(source)
        return sources
