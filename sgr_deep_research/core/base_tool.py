from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, ClassVar

from fastmcp import Client
from pydantic import BaseModel

# from sgr_deep_research.core.models import AgentStatesEnum
from sgr_deep_research.settings import get_config

if TYPE_CHECKING:
    from sgr_deep_research.core.models import ResearchContext

config = get_config()
logger = logging.getLogger(__name__)


class BaseTool(BaseModel):
    """Class to provide tool handling capabilities."""

    tool_name: ClassVar[str] = ""
    description: ClassVar[str] = ""

    async def __call__(self, context: ResearchContext) -> str:
        """Result should be a string or dumped json."""
        raise NotImplementedError("Execute method must be implemented by subclass")

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.tool_name:
            cls.tool_name = cls.__name__.lower()
        if not cls.description:
            cls.description = cls.__doc__ or ""


class MCPBaseTool(BaseTool):
    """Base model for MCP Tool schema."""

    _client: ClassVar[Client | None] = None

    async def __call__(self, _context) -> str:
        payload = self.model_dump()
        if self._client is None:
            return "Error: MCP client not initialized"
        try:
            async with self._client:  # type: ignore
                result = await self._client.call_tool(self.tool_name, payload)  # type: ignore
                return json.dumps([m.model_dump_json() for m in result.content], ensure_ascii=False)[
                    : config.mcp.context_limit
                ]
        except Exception as e:
            logger.error(f"Error processing MCP tool {self.tool_name}: {e}")
            return f"Error: {e}"
