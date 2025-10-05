"""
Confluence Vector Search Tools.

These tools provide semantic/vector search in Confluence knowledge base
using Smart Platform's KNN (K-Nearest Neighbors) capabilities.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import Field

from sgr_deep_research.core.tools.base import BaseTool
from sgr_deep_research.services.smart_platform_service import SmartPlatformService

if TYPE_CHECKING:
    from sgr_deep_research.core.models import ResearchContext

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ConfluenceVectorSearchTool(BaseTool):
    """Semantic vector search in Confluence knowledge base using KNN.
    
    This tool uses Smart Platform's KNN (K-Nearest Neighbors) algorithm to find 
    semantically relevant information in Confluence, even with different wording.
    
    Unlike full-text search, vector search understands meaning and context,
    making it ideal for:
    - Finding conceptually similar content
    - Semantic queries where exact keywords may vary
    - Context-aware information retrieval
    
    Best practices:
    - Use natural language queries that describe what you're looking for
    - Be specific about the type of information needed
    - The tool works well with both Russian and English queries
    - Results include both content and source references
    """
    
    reasoning: str = Field(description="Why using vector search and what information is expected")
    query: str = Field(description="Natural language search query describing what information is needed")

    def __init__(self, **data):
        super().__init__(**data)
        self._smart_platform_service = SmartPlatformService()

    def __call__(self, context: ResearchContext) -> str:
        """Execute Confluence vector search using KNN."""
        logger.info(f"🔍 Confluence vector search query: '{self.query}'")

        try:
            import asyncio
            
            # Get or create event loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run async search in current event loop
            if loop.is_running():
                # If loop is running, create task and wait for it
                import concurrent.futures
                import threading
                
                result_holder = {}
                exception_holder = {}
                
                def run_in_thread():
                    try:
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        result = new_loop.run_until_complete(
                            self._smart_platform_service.search(
                                query=self.query
                            )
                        )
                        result_holder['result'] = result
                        new_loop.close()
                    except Exception as e:
                        exception_holder['exception'] = e
                
                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join()
                
                if 'exception' in exception_holder:
                    raise exception_holder['exception']
                    
                result = result_holder['result']
            else:
                # Loop not running, use run_until_complete
                result = loop.run_until_complete(
                    self._smart_platform_service.search(
                        query=self.query
                    )
                )
            
            # Add sources to context for citations
            starting_number = len(context.sources) + 1
            for i, source in enumerate(result.sources, starting_number):
                from sgr_deep_research.core.models import SourceData
                
                # Extract source information
                source_id = source.get('id', '')
                source_content = source.get('content', '')
                source_type = source.get('type', 'unknown')
                source_name = source.get('name', 'Unknown Source')
                source_url = source.get('url', '')
                
                # Create SourceData-compatible entry
                source_data = SourceData(
                    number=i,
                    title=source_name,
                    url=source_url,
                    snippet=source_content[:500] if source_content else f"{source_type} - {source_name}",
                    full_content=source_content,
                    char_count=len(source_content) if source_content else 0,
                )
                context.sources[source_url or f"smart_platform_{source_id}"] = source_data
            
            # Format result
            formatted_result = f"Confluence Vector Search (KNN)\n"
            formatted_result += f"{'='*60}\n\n"
            formatted_result += f"Query: {self.query}\n"
            formatted_result += f"Agent ID: {self.agent_id}\n"
            formatted_result += f"Response ID: {result.response_id}\n"
            formatted_result += f"Timestamp: {result.send_at}\n\n"
            
            formatted_result += f"Response:\n{result.response}\n\n"
            
            formatted_result += f"Sources Found: {len(result.sources)}\n"
            formatted_result += f"{'='*60}\n\n"
            
            formatted_result += "Sources:\n\n"
            
            for i, source in enumerate(result.sources, 1):
                formatted_result += f"[{i}] {source.get('name', 'Unknown Source')}\n"
                formatted_result += f"    Type: {source.get('type', 'unknown')}\n"
                formatted_result += f"    ID: {source.get('id', 'N/A')}\n"
                
                if source.get('url'):
                    formatted_result += f"    URL: {source['url']}\n"
                
                # Show content preview
                content = source.get('content', '')
                if content:
                    content_preview = content[:300] + "..." if len(content) > 300 else content
                    formatted_result += f"    Content Preview:\n    {content_preview}\n"
                
                formatted_result += "\n"
            
            logger.info(f"✅ Confluence vector search completed, found {len(result.sources)} sources")
            return formatted_result
            
        except Exception as e:
            error_msg = (
                f"❌ Confluence vector search failed: {str(e)}\n\n"
                f"Possible reasons:\n"
                f"- Smart Platform service unavailable\n"
                f"- Invalid agent ID or credentials\n"
                f"- Network connectivity issues\n\n"
                f"Try using ConfluenceFullTextSearchTool as fallback."
            )
            logger.error(error_msg)
            return error_msg
        
        finally:
            # Clean up the service
            try:
                import asyncio
                import threading
                
                def cleanup():
                    try:
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        new_loop.run_until_complete(self._smart_platform_service.close())
                        new_loop.close()
                    except Exception:
                        pass
                
                thread = threading.Thread(target=cleanup)
                thread.start()
                thread.join(timeout=5)
            except Exception:
                pass


# Export tools
confluence_vector_search_tools = [
    ConfluenceVectorSearchTool,
]
