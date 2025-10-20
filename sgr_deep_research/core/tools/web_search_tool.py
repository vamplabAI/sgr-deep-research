from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import Field

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.models import SearchResult
from sgr_deep_research.services.tavily_search import TavilySearchService
from sgr_deep_research.settings import get_config

if TYPE_CHECKING:
    from sgr_deep_research.core.models import ResearchContext

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
config = get_config()


class WebSearchTool(BaseTool):
    """Search the web for real-time information about any topic.
    Use this tool when you need up-to-date information that might not be available in your training data,
    or when you need to verify current facts.
    The search results will include relevant snippets and URLs from web pages.
    This is particularly useful for questions about current events, technology updates,
    or any topic that requires recent information.
    Use for: Public information, news, market trends, external APIs, general knowledge
    Returns: Page titles, URLs, and short snippets (100 characters)
    Best for: Quick overview, finding relevant pages

    Usage:
        - Use SPECIFIC terms and context in queries
        - For acronyms, add context: "SGR Schema-Guided Reasoning"
        - Use quotes for exact phrases: "Structured Output OpenAI"
        - Search queries in SAME LANGUAGE as user request
        - For date/number questions, include specific year/context in query
        - Use ExtractPageContentTool to get full content from found URLs

    IMPORTANT FOR FACTUAL QUESTIONS:
        - Search snippets often contain direct answers - check them carefully
        - For questions with specific dates/numbers, snippets may be more accurate than full pages
        - If snippet directly answers the question, you may not need to extract full page
    """

    reasoning: str = Field(description="Why this search is needed and what to expect")
    query: str = Field(description="Search query in same language as user request")
    max_results: int = Field(
        default_factory=lambda: min(config.search.max_results, 10),
        description="Maximum results",
        ge=1,
        le=10,
    )

    def __init__(self, **data):
        super().__init__(**data)
        self._search_service = TavilySearchService()

    async def __call__(self, context: ResearchContext) -> str:
        """Execute web search using TavilySearchService."""

        logger.info(f"🔍 Search query: '{self.query}'")

        sources = await self._search_service.search(
            query=self.query,
            max_results=self.max_results,
            include_raw_content=False,
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
        formatted_result += "Search Results (titles, links, short snippets):\n\n"

        for source in sources:
            snippet = source.snippet[:100] + "..." if len(source.snippet) > 100 else source.snippet
            formatted_result += f"{str(source)}\n{snippet}\n\n"

        context.searches_used += 1
        logger.debug(formatted_result)
        return formatted_result
