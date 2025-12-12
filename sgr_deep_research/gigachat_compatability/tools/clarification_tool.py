from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from sgr_deep_research.gigachat_compatability.base_tool import BaseTool_functional
from sgr_deep_research.gigachat_compatability.models import ResearchContextCounted


class ClarificationTool_functional(BaseTool_functional):
    """Ask clarifying questions when facing ambiguous request.

    Keep all fields concise - brief reasoning, short terms, and clear questions.
    """

    tool_name: ClassVar[str] = "clarify_question"
    description: ClassVar[str] = "Задаю уточняющие вопросы при неоднозначном запросе."
    reasoning: str = Field(description="Why clarification is needed (1-2 sentences MAX)", max_length=200)
    unclear_terms: list[str] = Field(
        description="List of unclear terms (brief, 1-3 words each)",
        min_length=1,
        max_length=3,
    )
    assumptions: list[str] = Field(
        description="Possible interpretations (short, 1 sentence each)",
        min_length=2,
        max_length=3,
    )
    questions: list[str] = Field(
        description="3 specific clarifying questions (short and direct)",
        min_length=1,
        max_length=3,
    )

    async def __call__(self, context: ResearchContextCounted) -> str:
        return "\n".join(self.questions)
