from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import Field

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.models import SearchResult
from sgr_deep_research.core.tools_registry import tool
from sgr_deep_research.services.tavily_search import TavilySearchService
from sgr_deep_research.settings import get_config

if TYPE_CHECKING:
    from sgr_deep_research.core.models import ResearchContext

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
config = get_config()


@tool
class WebSearchTool(BaseTool):
    """Gather information.

    - Use SPECIFIC terms and context in search queries
    - For acronyms like "SGR", add context: "SGR Schema-Guided Reasoning"
    - Use quotes for exact phrases: "Structured Output OpenAI"
    - SEARCH QUERIES in SAME LANGUAGE as user request
    - scrape_content=True for deeper analysis (fetches full page content)
    """

    reasoning: str = Field(description="Why this search is needed and what to expect")
    query: str = Field(description="Search query in same language as user request")
    max_results: int = Field(default=10, description="Maximum results", ge=1, le=10)
    scrape_content: bool = Field(
        default=False,
        description="Fetch full page content for deeper analysis",
    )

    def __init__(self, **data):
        super().__init__(**data)
        self._search_service = TavilySearchService()

    def __call__(self, context: ResearchContext) -> str:
        """Execute web search using TavilySearchService."""

        logger.info(f"🔍 Search query: '{self.query}'")

        sources = self._search_service.search(
            query=self.query,
            max_results=self.max_results,
        )

        sources = TavilySearchService.rearrange_sources(sources, starting_number=len(context.sources) + 1)

        for source in sources:
            context.sources[source.url] = source

        search_result = SearchResult(
            query=self.query,
            answer=None,
            citations=sources,
            timestamp=datetime.now(),
        )
        context.searches.append(search_result)

        formatted_result = f"Search Query: {search_result.query}\n\n"

        if search_result.answer:
            formatted_result += f"AI Answer: {search_result.answer}\n\n"

        formatted_result += "Search Results:\n\n"

        for source in sources:
            if source.full_content:
                formatted_result += (
                    f"{str(source)}\n\n**Full Content (Markdown):**\n"
                    f"{source.full_content[: config.scraping.content_limit]}\n\n"
                )
            else:
                formatted_result += f"{str(source)}\n{source.snippet}\n\n"

        context.searches_used += 1
        logger.debug(formatted_result)
        return formatted_result
