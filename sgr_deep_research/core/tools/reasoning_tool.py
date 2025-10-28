from __future__ import annotations

from pydantic import Field

from sgr_deep_research.core.base_tool import BaseTool


class ReasoningTool(BaseTool):
    """Agent core logic, determines next reasoning step with adaptive planning
    by schema-guided-reasoning capabilities Keep all text fields concise and
    focused.

    Usage: Requiared tool use this tool before execution tool, and after execution
    """

    # Reasoning chain - step-by-step thinking process (helps stabilize model)
    reasoning_steps: list[str] = Field(
        description="Step-by-step reasoning (brief, 1 sentence each)",
        min_length=2,
        max_length=3,
    )

    # Reasoning and state assessment
    current_situation: str = Field(
        description="Current research situation (2-3 sentences MAX)",
        max_length=300,
    )
    plan_status: str = Field(
        description="Status of current plan (1 sentence)",
        max_length=150,
    )
    enough_data: bool = Field(
        default=False,
        description="Sufficient data collected for comprehensive report?",
    )

    # Next step planning
    remaining_steps: list[str] = Field(
        description="1-3 remaining steps (brief, action-oriented)",
        min_length=1,
        max_length=3,
    )
    task_completed: bool = Field(description="Is the research task finished?")

    async def __call__(self, *args, **kwargs):
        return self.model_dump_json(
            indent=2,
        )
