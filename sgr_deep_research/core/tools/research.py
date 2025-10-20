from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from pydantic import Field

from sgr_deep_research.core.models import SearchResult
from sgr_deep_research.core.tools.base import BaseTool
from sgr_deep_research.services.tavily_search import TavilySearchService
from sgr_deep_research.settings import get_config

if TYPE_CHECKING:
    from sgr_deep_research.core.models import ResearchContext

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
config = get_config()


class CreateReportTool(BaseTool):
    """Create comprehensive detailed report with citations as a final step of
    research.

    CRITICAL: Every factual claim in content MUST have inline citations [1], [2], [3].
    Citations must be integrated directly into sentences, not just listed at the end.
    """

    reasoning: str = Field(description="Why ready to create report now")
    title: str = Field(description="Report title")
    user_request_language_reference: str = Field(
        description="Copy of original user request to ensure language consistency"
    )
    content: str = Field(
        description="Write comprehensive research report following the REPORT CREATION GUIDELINES from system prompt. "
        "Use the SAME LANGUAGE as user_request_language_reference. "
        "MANDATORY: Include inline citations [1], [2], [3] after EVERY factual claim. "
        "Example: 'The system uses Vue.js [1] and Python [2].' NOT: 'The system uses Vue.js and Python.'"
    )
    confidence: Literal["high", "medium", "low"] = Field(description="Confidence in findings")

    async def __call__(self, context: ResearchContext) -> str:
        # Save report
        reports_dir = config.execution.reports_dir
        os.makedirs(reports_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in self.title if c.isalnum() or c in (" ", "-", "_"))[:50]
        filename = f"{timestamp}_{safe_title}.md"
        filepath = os.path.join(reports_dir, filename)

        # Format full report with sources
        full_content = f"# {self.title}\n\n"
        full_content += f"*Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
        full_content += self.content + "\n\n"

        # Add sources reference section
        if context.sources:
            full_content += "---\n\n"
            full_content += "## Источники / Sources\n\n"
            full_content += "\n".join([str(source) for source in context.sources.values()])

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_content)

        report = {
            "title": self.title,
            "content": self.content,
            "confidence": self.confidence,
            "sources_count": len(context.sources),
            "word_count": len(self.content.split()),
            "filepath": filepath,
            "timestamp": datetime.now().isoformat(),
        }
        logger.info(
            "📝 CREATE REPORT FULL DEBUG:\n"
            f"   🌍 Language Reference: '{self.user_request_language_reference}'\n"
            f"   📊 Title: '{self.title}'\n"
            f"   🔍 Reasoning: '{self.reasoning[:150]}...'\n"
            f"   📈 Confidence: {self.confidence}\n"
            f"   📄 Content Preview: '{self.content[:200]}...'\n"
            f"   📊 Words: {report['word_count']}, Sources: {report['sources_count']}\n"
            f"   💾 Saved: {filepath}\n"
        )
        return json.dumps(report, indent=2, ensure_ascii=False)


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
                    content_preview = source.full_content[: config.scraping.content_limit]
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


research_agent_tools = [
    WebSearchTool,
    ExtractPageContentTool,
    CreateReportTool,
]
