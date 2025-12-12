from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from sgr_deep_research.gigachat_compatability.base_tool import BaseTool_functional
from sgr_deep_research.gigachat_compatability.models import ResearchContextCounted


class AdaptPlanTool_functional(BaseTool_functional):
    """Adapt research plan based on new findings."""

    tool_name: ClassVar[str] = "adapt_plan"
    description: ClassVar[str] = "Адаптирую план исследования на основе новых данных."
    reasoning: str = Field(description="Why plan needs adaptation based on new data")
    original_goal: str = Field(description="Original research goal")
    new_goal: str = Field(description="Updated research goal")
    plan_changes: list[str] = Field(description="Specific changes made to plan", min_length=1, max_length=3)
    next_steps: list[str] = Field(description="Updated remaining steps", min_length=2, max_length=4)

    async def __call__(self, context: ResearchContextCounted) -> str:
        return self.model_dump_json(
            indent=2,
            exclude={
                "reasoning",
            },
        )
