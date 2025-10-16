from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import Field

from sgr_deep_research.core.base_tool import BaseTool

if TYPE_CHECKING:
    from sgr_deep_research.core.models import ResearchContext


class ClarificationTool(BaseTool):
    """Ask clarifying questions when facing ambiguous request."""

    reasoning: str = Field(description="Why clarification is needed")
    unclear_terms: list[str] = Field(description="List of unclear terms or concepts", min_length=1, max_length=5)
    assumptions: list[str] = Field(description="Possible interpretations to verify", min_length=2, max_length=4)
    questions: list[str] = Field(description="3-5 specific clarifying questions", min_length=3, max_length=5)

    async def __call__(self, context: ResearchContext) -> str:
        return "\n".join(self.questions)
