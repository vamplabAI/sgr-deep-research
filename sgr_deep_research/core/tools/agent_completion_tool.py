from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import Field

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.models import AgentStatesEnum

if TYPE_CHECKING:
    from sgr_deep_research.core.models import ResearchContext


class AgentCompletionTool(BaseTool):
    """Finalize research task and complete agent execution after all steps are
    completed."""

    reasoning: str = Field(description="Why task is now complete")
    completed_steps: list[str] = Field(description="Summary of completed steps", min_length=1, max_length=5)
    status: Literal[AgentStatesEnum.COMPLETED, AgentStatesEnum.FAILED] = Field(description="Task completion status")

    async def __call__(self, context: ResearchContext) -> str:
        context.state = self.status
        return self.model_dump_json(
            indent=2,
        )
