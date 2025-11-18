from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Literal

from pydantic import Field

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.models import AgentStatesEnum

if TYPE_CHECKING:
    from sgr_deep_research.core.models import ResearchContext

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class FinalAnswerTool(BaseTool):
    """Provide final answer OR ask clarifying questions when needed.
    
    Usage:
    1. For FINAL ANSWER: Set answer_type='final_answer' with comprehensive answer
    2. For CLARIFICATION: Set answer_type='clarification' with questions to ask user
    
    The user's response to clarification questions will appear in the conversation history.
    After receiving clarification, analyze the full conversation and provide the final answer.
    """

    reasoning: str = Field(description="Why providing this response (answer or clarification needed)")
    completed_steps: list[str] = Field(
        description="Summary of completed steps so far", min_length=1, max_length=5
    )
    answer_type: Literal["final_answer", "clarification"] = Field(
        description="Type of response: 'final_answer' for completing task, 'clarification' for asking questions"
    )
    answer: str = Field(
        description="Final comprehensive answer with EXACT details OR clarifying questions for user (numbered list)"
    )
    status: Literal[AgentStatesEnum.COMPLETED, AgentStatesEnum.FAILED] = Field(
        default=AgentStatesEnum.COMPLETED,
        description="Task completion status (only relevant for final_answer type)"
    )

    def _format_answer_with_sources(self, context: ResearchContext) -> str:
        """Format answer with clickable markdown links for sources."""
        answer = self.answer
        
        # Convert [1], [2] citations to markdown links if sources exist
        if context.sources:
            # Pattern: [1] or [2] etc.
            def replace_citation(match):
                num = int(match.group(1))
                # Find source by number
                for source in context.sources.values():
                    if source.number == num:
                        # Format as markdown link: [[1] Title](URL)
                        return f"[[{num}] {source.title}]({source.url})"
                return match.group(0)  # Return original if not found
            
            answer = re.sub(r'\[(\d+)\]', replace_citation, answer)
        
        return answer
    
    async def __call__(self, context: ResearchContext) -> str:
        if self.answer_type == "final_answer":
            context.state = self.status
            # Format answer with clickable links
            formatted_answer = self._format_answer_with_sources(context)
            context.execution_result = formatted_answer
        else:
            # For clarification, we complete but the answer contains questions
            context.state = AgentStatesEnum.COMPLETED
            context.execution_result = self.answer
            
        return self.model_dump_json(indent=2)
