from __future__ import annotations

from pydantic import Field

from sgr_deep_research.core.base_tool import BaseTool


class ReasoningTool(BaseTool):
    """Agent Core - Determines next reasoning step with adaptive planning."""

    # Reasoning chain - step-by-step thinking process (helps stabilize model)
    reasoning_steps: list[str] = Field(
        description="Step-by-step reasoning process leading to decision", min_length=2, max_length=4
    )

    # Reasoning and state assessment
    current_situation: str = Field(description="Current research situation analysis")
    plan_status: str = Field(description="Status of current plan execution")
    enough_data: bool = Field(
        default=False,
        description="Sufficient data collected for comprehensive report?",
    )

    # Next step planning
    remaining_steps: list[str] = Field(description="1-3 remaining steps to complete task", min_length=1, max_length=3)
    task_completed: bool = Field(description="Is the research task finished?")

    def __call__(self, *args, **kwargs):
        return self.model_dump_json(
            indent=2,
        )
