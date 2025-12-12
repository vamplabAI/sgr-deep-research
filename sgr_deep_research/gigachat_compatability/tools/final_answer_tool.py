from __future__ import annotations

import logging
from typing import Literal, ClassVar

from pydantic import Field

from sgr_deep_research.gigachat_compatability.base_tool import BaseTool_functional
from sgr_deep_research.gigachat_compatability.models import AgentStatesEnum, ResearchContextCounted

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class FinalAnswerTool_functional(BaseTool_functional):
    """Finalize research task and complete agent execution after all steps are
    completed.

    Usage: Call after you complete research task
    """

    tool_name: ClassVar[str] = "final_answer"
    description: ClassVar[str] = "Завершаю исследовательскую задачу и выполняю завершение работы агента после выполнения всех шагов."
    reasoning: str = Field(description="Why task is now complete and how answer was verified")
    completed_steps: list[str] = Field(
        description="Summary of completed steps including verification", min_length=1, max_length=5
    )
    answer: str = Field(description="result of the research AS merge of tools' answers: NO INFO DROPPED, NO MODIFICATIONS")
    status: Literal[AgentStatesEnum.COMPLETED, AgentStatesEnum.FAILED] = Field(description="Task completion status")

    async def __call__(self, context: ResearchContextCounted) -> str:
        context.state = self.status
        context.execution_result = self.answer
        return self.model_dump_json(
            indent=2,
        )
