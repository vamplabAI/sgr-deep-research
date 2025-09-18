from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from sgr_deep_research.core.models import ResearchContext


class BaseTool(BaseModel):
    """Class to provide tool handling capabilities."""
    is_enabled: ClassVar[bool] = True
    tool_name: ClassVar[str] = None
    description: ClassVar[str] = None

    def __call__(self, context: ResearchContext) -> str:
        """Result should be a string or dumped json."""
        raise NotImplementedError("Execute method must be implemented by subclass")

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.tool_name = cls.tool_name or cls.__name__.lower()
        cls.description = cls.description or cls.__doc__ or ""
