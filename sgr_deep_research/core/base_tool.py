from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from sgr_deep_research.core.models import ResearchContext


class BaseTool(BaseModel):
    """Base class for all tools providing interface for tool handling capabilities."""

    tool_name: ClassVar[str | None] = None
    description: ClassVar[str | None] = None
    is_system_tool: ClassVar[bool] = False

    def __call__(self, context: ResearchContext) -> str:
        """Execute tool with given context. Result should be a string or dumped json.
        
        Args:
            context: Research context containing state, sources, and other data
            
        Returns:
            String result of tool execution
        """
        raise NotImplementedError("Execute method must be implemented by subclass")

    def __init_subclass__(cls, **kwargs):
        """Automatically set tool_name and description for subclasses."""
        super().__init_subclass__(**kwargs)
        cls.tool_name = cls.tool_name or cls.__name__.lower()
        cls.description = cls.description or cls.__doc__ or ""
