import logging
from typing import Literal

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel

from sgr_deep_research.settings import get_config

logger = logging.getLogger(__name__)


class ConfluencePageData(BaseModel):
    """Data about a Confluence page."""

    id: str
    type: str
    title: str
    space_name: str | None = None
    space_key: str | None = None
    url: str
    html_content: str | None = None
    text_content: str | None = None
    version: int | None = None
    last_updated: str | None = None
    author: str | None = None


class ConfluenceSearchResult(BaseModel):
    """Confluence search result."""

    query: str
    total_size: int
    pages: list[ConfluencePageData]
    search_duration: int | None = None


class ConfluenceService:
    """Service for interacting with Confluence REST API."""

    def __init__(self):
        config = get_config()
        self._base_url = config.confluence.base_url
        self._username = config.confluence.username
        self._password = config.confluence.password
        self._timeout = config.confluence.timeout

    def _get_client(self) -> httpx.Client:
        """Create HTTP client with authentication."""
        return httpx.Client(
            auth=(self._username, self._password),
            timeout=self._timeout,
            follow_redirects=True,
        )

    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML content to plain text."""
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text
        text = soup.get_text()

        # Clean up whitespace and newlines
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = "\n".join(chunk for chunk in chunks if chunk)

        return text

    def _parse_page_data(self, page_json: dict, include_content: bool = False) -> ConfluencePageData:
        """Parse page data from Confluence API response."""
        page_id = page_json.get("id", "")
        title = page_json.get("title", "Untitled")
        page_type = page_json.get("type", "page")

        # Space information
        space = page_json.get("space", {})
        space_name = space.get("name") if space else None
        space_key = space.get("key") if space else None

        # URL
        web_ui = page_json.get("_links", {}).get("webui", "")
        url = f"{self._base_url}{web_ui}" if web_ui else ""

        # Version and history
        version_data = page_json.get("version", {})
        version = version_data.get("number")

        history = page_json.get("history", {})
        last_updated_data = history.get("lastUpdated", {})
        last_updated = last_updated_data.get("when")
        author_data = last_updated_data.get("by", {})
        author = author_data.get("displayName")

        # Content
        html_content = None
        text_content = None

        if include_content:
            body = page_json.get("body", {})
            view = body.get("view", {})
            if view:
                html_content = view.get("value", "")
                if html_content:
                    text_content = self._html_to_text(html_content)

        return ConfluencePageData(
            id=page_id,
            type=page_type,
            title=title,
            space_name=space_name,
            space_key=space_key,
            url=url,
            html_content=html_content,
            text_content=text_content,
            version=version,
            last_updated=last_updated,
            author=author,
        )

    def search(
        self,
        query: str,
        limit: int = 10,
        space: str | None = None,
        content_type: Literal["page", "blogpost", "attachment"] = "page",
        include_content: bool = False,
    ) -> ConfluenceSearchResult:
        """Search Confluence content.

        Args:
            query: Search query
            limit: Maximum number of results
            space: Filter by space key (optional)
            content_type: Type of content to search
            include_content: Include full page content in results

        Returns:
            ConfluenceSearchResult with found pages
        """
        # Build CQL query
        cql_parts = [f'siteSearch~"{query}"']

        if content_type:
            cql_parts.append(f"type={content_type}")

        if space:
            cql_parts.append(f"space={space}")

        cql_query = " AND ".join(cql_parts)

        # Build request parameters
        params = {
            "cql": cql_query,
            "limit": limit,
        }

        if include_content:
            params["expand"] = "body.view,space,version,history"

        logger.info(f"🔍 Confluence search: '{query}' in space='{space or 'all'}' (limit={limit})")

        try:
            with self._get_client() as client:
                response = client.get(
                    f"{self._base_url}/rest/api/content/search",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

            # Parse results
            pages = []
            for result in data.get("results", []):
                page = self._parse_page_data(result, include_content=include_content)
                pages.append(page)

            return ConfluenceSearchResult(
                query=cql_query,
                total_size=data.get("totalSize", 0),
                pages=pages,
                search_duration=data.get("searchDuration"),
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Confluence API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"❌ Confluence search error: {e}")
            raise

    def get_page(self, page_id: str, include_content: bool = True) -> ConfluencePageData:
        """Get specific Confluence page by ID.

        Args:
            page_id: Confluence page ID
            include_content: Include page content

        Returns:
            ConfluencePageData with page information and content
        """
        params = {}
        if include_content:
            params["expand"] = "body.view,space,version,history"

        logger.info(f"📄 Getting Confluence page: {page_id}")

        try:
            with self._get_client() as client:
                response = client.get(
                    f"{self._base_url}/rest/api/content/{page_id}",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

            return self._parse_page_data(data, include_content=include_content)

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Confluence API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"❌ Confluence get page error: {e}")
            raise

    def get_space_pages(
        self,
        space_key: str,
        limit: int = 25,
        include_content: bool = False,
    ) -> list[ConfluencePageData]:
        """Get all pages from a specific space.

        Args:
            space_key: Space key (e.g., 'NDTALL')
            limit: Maximum number of pages to retrieve
            include_content: Include page content

        Returns:
            List of ConfluencePageData
        """
        params = {
            "spaceKey": space_key,
            "limit": limit,
        }

        if include_content:
            params["expand"] = "body.view,space,version,history"

        logger.info(f"📚 Getting pages from space: {space_key} (limit={limit})")

        try:
            with self._get_client() as client:
                response = client.get(
                    f"{self._base_url}/rest/api/content",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

            pages = []
            for result in data.get("results", []):
                page = self._parse_page_data(result, include_content=include_content)
                pages.append(page)

            logger.info(f"✅ Retrieved {len(pages)} pages from space {space_key}")
            return pages

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Confluence API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"❌ Confluence get space pages error: {e}")
            raise
