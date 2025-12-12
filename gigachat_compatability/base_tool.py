from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, ClassVar

# from fastmcp import Client
from pydantic import BaseModel

from sgr_deep_research.core.agent_config import GlobalConfig
from sgr_deep_research.core.services.registry import ToolRegistry
from sgr_deep_research.core.base_tool import BaseTool

if TYPE_CHECKING:
    from sgr_deep_research.core.models import ResearchContext


logger = logging.getLogger(__name__)


class ToolRegistryMixin:
    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if cls.__name__ not in ("BaseTool_functional", "MCPBaseTool"):
            ToolRegistry.register(cls, name=cls.tool_name)


class BaseTool_functional(BaseTool, ToolRegistryMixin):
    """Class to provide tool handling capabilities."""

    tool_name: ClassVar[str] = None
    description: ClassVar[str] = None

    async def __call__(self, context: ResearchContext) -> str:
        """Result should be a string or dumped json."""
        raise NotImplementedError("Execute method must be implemented by subclass")

    def __init_subclass__(cls, **kwargs) -> None:
        cls.tool_name = cls.tool_name or cls.__name__.lower()
        cls.description = cls.description or cls.__doc__ or ""
        super().__init_subclass__(**kwargs)