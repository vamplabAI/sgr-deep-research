from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import Field

from sgr_deep_research.core.agent_config import GlobalConfig
from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.services.tavily_search import TavilySearchService

if TYPE_CHECKING:
    from sgr_deep_research.core.models import ResearchContext

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ExtractPageContentTool(BaseTool):
    """Extract full detailed content from specific web pages.
     Use for: Getting complete page content from URLs found in web search Returns:
     Full page content in readable format (via Tavily Extract API)
     Best for: Deep analysis of specific pages, extracting structured data

    Usage: Call after WebSearchTool to get detailed information from promising URLs

    CRITICAL WARNINGS:
        - Extracted pages may show data from DIFFERENT years/time periods than asked
        - ALWAYS verify that extracted content matches the question's temporal context
        - Example: Question asks about 2022, but page shows 2024 data - REJECT this source
        - If extracted content contradicts search snippet, prefer snippet for factual questions
        - For date/number questions, cross-check extracted values with search snippets
    """

    reasoning: str = Field(description="Why extract these specific pages")
    urls: list[str] = Field(description="List of URLs to extract full content from", min_length=1, max_length=5)

    def __init__(self, **data):
        super().__init__(**data)
        self._search_service = TavilySearchService()

    async def __call__(self, context: ResearchContext) -> str:
        """Extract full content from specified URLs."""

        logger.info(f"📄 Extracting content from {len(self.urls)} URLs")

        sources = await self._search_service.extract(urls=self.urls)

        # Update existing sources instead of overwriting
        for source in sources:
            if source.url in context.sources:
                # URL already exists, update with full content but keep original number
                existing = context.sources[source.url]
                existing.full_content = source.full_content
                existing.char_count = source.char_count
            else:
                # New URL, add with next number
                source.number = len(context.sources) + 1
                context.sources[source.url] = source

        formatted_result = "Extracted Page Content:\n\n"

        # Format results using sources from context (to get correct numbers)
        for url in self.urls:
            if url in context.sources:
                source = context.sources[url]
                if source.full_content:
                    content_preview = source.full_content[: GlobalConfig().search.content_limit]
                    formatted_result += (
                        f"{str(source)}\n\n**Full Content:**\n"
                        f"{content_preview}\n\n"
                        f"*[Content length: {len(content_preview)} characters]*\n\n"
                        "---\n\n"
                    )
                else:
                    formatted_result += f"{str(source)}\n*Failed to extract content*\n\n"

        logger.debug(formatted_result[:500])
        return formatted_result
