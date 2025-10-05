from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from pydantic import Field

from sgr_deep_research.core.tools.base import BaseTool
from sgr_deep_research.services.confluence_service import ConfluenceService

if TYPE_CHECKING:
    from sgr_deep_research.core.models import ResearchContext

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ConfluenceFullTextSearchTool(BaseTool):
    """Full-text search in Confluence knowledge base for internal documentation.

    Use this tool to find internal documentation, technical guides, project info,
    architecture docs, and other knowledge stored in company Confluence using full-text search.

    Best practices:
    - Use specific technical terms and project names
    - Search queries in SAME LANGUAGE as user request
    - For Russian requests use Russian: "архитектура SmartPlatform"
    - For English requests use English: "SmartPlatform architecture"
    - include_content=True when you need full page text for analysis
    """

    tool_name: str = "confluence_full_text_search"
    description: str = "Full-text search in Confluence for internal documentation using keyword matching"

    reasoning: str = Field(description="Why searching Confluence and what information is expected")
    query: str = Field(description="Search query in same language as user request")
    max_results: int = Field(default=10, description="Maximum results", ge=1, le=25)
    content_type: Literal["page", "blogpost", "attachment"] = Field(
        default="page",
        description="Type of content to search",
    )
    include_content: bool = Field(
        default=False,
        description="Include full page content for deeper analysis (slower but more detailed)",
    )

    def __init__(self, **data):
        super().__init__(**data)
        self._confluence_service = ConfluenceService()

    def __call__(self, context: ResearchContext) -> str:
        """Execute Confluence search."""
        logger.info(f"🔍 Confluence search query: '{self.query}'")

        result = self._confluence_service.search(
            query=self.query,
            limit=self.max_results,
            content_type=self.content_type,
            include_content=self.include_content,
        )

        # Add pages to context sources for citations
        starting_number = len(context.sources) + 1
        for i, page in enumerate(result.pages, starting_number):
            # Create SourceData-compatible entry
            from sgr_deep_research.core.models import SourceData
            
            source = SourceData(
                number=i,
                title=page.title,
                url=page.url,
                snippet=page.text_content[:500] if page.text_content else f"{page.space_name or ''} - {page.type}",
                full_content=page.text_content or "",
                char_count=len(page.text_content) if page.text_content else 0,
            )
            context.sources[page.url] = source

        formatted_result = f"Confluence Search Query: {self.query}\n"
        formatted_result += f"Total Found: {result.total_size} items\n"
        formatted_result += f"Showing: {len(result.pages)} results\n\n"

        if result.search_duration:
            formatted_result += f"Search Duration: {result.search_duration}ms\n\n"

        formatted_result += "Results:\n\n"

        for i, page in enumerate(result.pages, 1):
            formatted_result += f"[{i}] {page.title}\n"
            formatted_result += f"    Page ID: {page.id}\n"  # IMPORTANT: Show Page ID first
            formatted_result += f"    Type: {page.type}\n"

            if page.space_name:
                formatted_result += f"    Space: {page.space_name} ({page.space_key})\n"

            formatted_result += f"    URL: {page.url}\n"

            if page.version:
                formatted_result += f"    Version: {page.version}\n"

            if page.last_updated:
                formatted_result += f"    Updated: {page.last_updated}"
                if page.author:
                    formatted_result += f" by {page.author}"
                formatted_result += "\n"

            if self.include_content and page.text_content:
                content_preview = page.text_content[:500]
                formatted_result += f"    Content Preview:\n    {content_preview}...\n"

            formatted_result += "\n"

        logger.info(f"✅ Found {len(result.pages)} Confluence pages, added to sources")
        return formatted_result


class ConfluenceSpaceFullTextSearchTool(BaseTool):
    """Full-text search within specific Confluence space for targeted information.

    Use when you know the specific space (project/team area) to search in.
    More precise than general search when space is known.

    Common spaces:
    - NDTALL - NDT Smart Platform documentation
    - NH - General project documentation
    - BAN - Banking projects
    """

    tool_name: str = "confluence_space_full_text_search"
    description: str = "Full-text search within specific Confluence space using keyword matching"

    reasoning: str = Field(description="Why searching this specific space")
    query: str = Field(description="Search query in same language as user request")
    space_key: str = Field(description="Confluence space key (e.g., 'NDTALL', 'NH', 'BAN')")
    max_results: int = Field(default=10, description="Maximum results", ge=1, le=25)
    include_content: bool = Field(
        default=False,
        description="Include full page content for deeper analysis",
    )

    def __init__(self, **data):
        super().__init__(**data)
        self._confluence_service = ConfluenceService()

    def __call__(self, context: ResearchContext) -> str:
        """Execute Confluence space search."""
        logger.info(f"🔍 Confluence space search: '{self.query}' in space '{self.space_key}'")

        result = self._confluence_service.search(
            query=self.query,
            limit=self.max_results,
            space=self.space_key,
            content_type="page",
            include_content=self.include_content,
        )

        # Add pages to context sources for citations
        starting_number = len(context.sources) + 1
        for i, page in enumerate(result.pages, starting_number):
            from sgr_deep_research.core.models import SourceData
            
            source = SourceData(
                number=i,
                title=page.title,
                url=page.url,
                snippet=page.text_content[:500] if page.text_content else f"{page.space_name or ''} - {page.type}",
                full_content=page.text_content or "",
                char_count=len(page.text_content) if page.text_content else 0,
            )
            context.sources[page.url] = source

        formatted_result = f"Confluence Space Search\n"
        formatted_result += f"Query: {self.query}\n"
        formatted_result += f"Space: {self.space_key}\n"
        formatted_result += f"Total Found: {result.total_size} pages\n"
        formatted_result += f"Showing: {len(result.pages)} results\n\n"

        formatted_result += "Results:\n\n"

        for i, page in enumerate(result.pages, 1):
            formatted_result += f"[{i}] {page.title}\n"
            formatted_result += f"    Page ID: {page.id}\n"
            formatted_result += f"    URL: {page.url}\n"

            if page.version:
                formatted_result += f"    Version: {page.version}\n"

            if page.last_updated:
                formatted_result += f"    Updated: {page.last_updated}"
                if page.author:
                    formatted_result += f" by {page.author}"
                formatted_result += "\n"

            if self.include_content and page.text_content:
                content_preview = page.text_content[:500]
                formatted_result += f"    Content:\n    {content_preview}...\n"

            formatted_result += "\n"

        logger.info(f"✅ Found {len(result.pages)} pages in space {self.space_key}, added to sources")
        return formatted_result


class ConfluencePageRetrievalTool(BaseTool):
    """Retrieve full content of specific Confluence page by ID.

    Use when you have page ID from search results and need complete page content.
    This provides full text, not just preview.

    Get page ID from:
    - Previous ConfluenceSearchTool results (use 'Page ID' field)
    - Previous ConfluenceSpaceSearchTool results (use 'Page ID' field)
    - Direct URL (pageId parameter in URL)
    
    IMPORTANT: Page ID must be a numeric string like '123456789', NOT space keys like 'GPP' or paths like 'GPP/PageName'.
    """

    reasoning: str = Field(description="Why retrieving this specific page")
    page_id: str = Field(
        description="Confluence page ID - MUST be numeric string (e.g., '123456789'). "
        "Get it from search results 'Page ID' field or URL 'pageId' parameter. "
        "NOT space key (like 'GPP') or page path (like 'GPP/Zaman')."
    )

    def __init__(self, **data):
        super().__init__(**data)
        self._confluence_service = ConfluenceService()

    def __call__(self, context: ResearchContext) -> str:
        """Retrieve Confluence page content."""
        
        # Validate page_id format
        if not self.page_id.isdigit():
            error_msg = (
                f"❌ Invalid page_id format: '{self.page_id}'\n\n"
                f"Page ID must be numeric (e.g., '123456789'), not a space key or path.\n"
                f"To get the correct page ID:\n"
                f"1. Use ConfluenceSearchTool or ConfluenceSpaceSearchTool first\n"
                f"2. Look for 'Page ID' field in results\n"
                f"3. Use that numeric ID with this tool\n\n"
                f"Example: If search shows 'Page ID: 123456789', use '123456789' not 'GPP/Zaman'."
            )
            logger.error(error_msg)
            return error_msg
        
        logger.info(f"📄 Retrieving Confluence page: {self.page_id}")

        try:
            page = self._confluence_service.get_page(
                page_id=self.page_id,
                include_content=True,
            )
        except Exception as e:
            error_msg = (
                f"❌ Failed to retrieve page {self.page_id}: {str(e)}\n\n"
                f"Possible reasons:\n"
                f"- Page doesn't exist or was deleted\n"
                f"- No access permissions to this page\n"
                f"- Invalid page ID\n\n"
                f"Try using ConfluenceSearchTool to find the correct page."
            )
            logger.error(error_msg)
            return error_msg

        # Add page to context sources for citations
        from sgr_deep_research.core.models import SourceData
        
        # Check if this page is already in sources, if not add it
        if page.url not in context.sources:
            starting_number = len(context.sources) + 1
            source = SourceData(
                number=starting_number,
                title=page.title,
                url=page.url,
                snippet=page.text_content[:500] if page.text_content else f"{page.space_name or ''} - {page.type}",
                full_content=page.text_content or "",
                char_count=len(page.text_content) if page.text_content else 0,
            )
            context.sources[page.url] = source

        formatted_result = f"Confluence Page\n"
        formatted_result += f"{'='*80}\n\n"
        formatted_result += f"Title: {page.title}\n"
        formatted_result += f"ID: {page.id}\n"
        formatted_result += f"Type: {page.type}\n"

        if page.space_name:
            formatted_result += f"Space: {page.space_name} ({page.space_key})\n"

        formatted_result += f"URL: {page.url}\n"

        if page.version:
            formatted_result += f"Version: {page.version}\n"

        if page.last_updated:
            formatted_result += f"Last Updated: {page.last_updated}"
            if page.author:
                formatted_result += f" by {page.author}"
            formatted_result += "\n"

        formatted_result += f"\n{'='*80}\n\n"

        if page.text_content:
            formatted_result += "Content:\n\n"
            formatted_result += page.text_content
        else:
            formatted_result += "No content available.\n"

        logger.info(f"✅ Retrieved page: {page.title}, added to sources")
        return formatted_result


confluence_full_text_search_tools = [
    ConfluenceFullTextSearchTool,
    ConfluenceSpaceFullTextSearchTool,
    ConfluencePageRetrievalTool,
]
