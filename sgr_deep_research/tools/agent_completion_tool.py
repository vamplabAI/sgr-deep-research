from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Literal

from pydantic import Field

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.models import AgentStatesEnum
from sgr_deep_research.core.tools_registry import tool

if TYPE_CHECKING:
    from sgr_deep_research.core.models import ResearchContext


@tool
class AgentCompletionTool(BaseTool):
    """Tool for completing agent execution with status."""

    is_system_tool: ClassVar[bool] = True

    reasoning: str = Field(description="Why task is now complete")
    completed_steps: list[str] = Field(description="Summary of completed steps", min_length=1, max_length=5)
    status: Literal[AgentStatesEnum.COMPLETED, AgentStatesEnum.FAILED] = Field(description="Task completion status")

    def __call__(self, context: ResearchContext) -> str:
        context.state = self.status
        return self.model_dump_json(
            indent=2,
        )
