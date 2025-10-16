from __future__ import annotations

import json
import logging
import operator
from abc import ABC
from functools import reduce
from typing import TYPE_CHECKING, Annotated, ClassVar, Literal, Type, TypeVar

from fastmcp import Client
from pydantic import BaseModel, Field, create_model

from sgr_deep_research.core.models import AgentStatesEnum
from sgr_deep_research.settings import get_config

if TYPE_CHECKING:
    from sgr_deep_research.core.models import ResearchContext

config = get_config()
logger = logging.getLogger(__name__)


class BaseTool(BaseModel):
    """Class to provide tool handling capabilities."""

    tool_name: ClassVar[str] = None
    description: ClassVar[str] = None

    async def __call__(self, context: ResearchContext) -> str:
        """Result should be a string or dumped json."""
        raise NotImplementedError("Execute method must be implemented by subclass")

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.tool_name = cls.tool_name or cls.__name__.lower()
        cls.description = cls.description or cls.__doc__ or ""


class MCPBaseTool(BaseTool):
    """Base model for MCP Tool schema."""

    _client: ClassVar[Client | None] = None

    async def __call__(self, _context) -> str:
        payload = self.model_dump()
        try:
            async with self._client:
                result = await self._client.call_tool(self.tool_name, payload)
                return json.dumps([m.model_dump_json() for m in result.content], ensure_ascii=False)[
                    : config.mcp.context_limit
                ]
        except Exception as e:
            logger.error(f"Error processing MCP tool {self.tool_name}: {e}")
            return f"Error: {e}"


class ClarificationTool(BaseTool):
    """Ask clarifying questions when facing ambiguous request.

    Keep all fields concise - brief reasoning, short terms, and clear questions.
    """

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
        min_length=3,
        max_length=3,
    )

    async def __call__(self, context: ResearchContext) -> str:
        return "\n".join(self.questions)


class GeneratePlanTool(BaseTool):
    """Generate research plan.

    Useful to split complex request into manageable steps.
    """

    reasoning: str = Field(description="Justification for research approach")
    research_goal: str = Field(description="Primary research objective")
    planned_steps: list[str] = Field(description="List of 3-4 planned steps", min_length=3, max_length=4)
    search_strategies: list[str] = Field(description="Information search strategies", min_length=2, max_length=3)

    async def __call__(self, context: ResearchContext) -> str:
        return self.model_dump_json(
            indent=2,
            exclude={
                "reasoning",
            },
        )


class AdaptPlanTool(BaseTool):
    """Adapt research plan based on new findings."""

    reasoning: str = Field(description="Why plan needs adaptation based on new data")
    original_goal: str = Field(description="Original research goal")
    new_goal: str = Field(description="Updated research goal")
    plan_changes: list[str] = Field(description="Specific changes made to plan", min_length=1, max_length=3)
    next_steps: list[str] = Field(description="Updated remaining steps", min_length=2, max_length=4)

    async def __call__(self, context: ResearchContext) -> str:
        return self.model_dump_json(
            indent=2,
            exclude={
                "reasoning",
            },
        )


class FinalAnswerTool(BaseTool):
    """Finalize research task and complete agent execution after all steps are
    completed.

    Usage: Call after you complete research task
    """

    reasoning: str = Field(description="Why task is now complete and how answer was verified")
    completed_steps: list[str] = Field(
        description="Summary of completed steps including verification", min_length=1, max_length=5
    )
    answer: str = Field(description="Comprehensive final answer with EXACT factual details (dates, numbers, names)")
    status: Literal[AgentStatesEnum.COMPLETED, AgentStatesEnum.FAILED] = Field(description="Task completion status")

    async def __call__(self, context: ResearchContext) -> str:
        context.state = self.status
        context.execution_result = self.answer
        return self.model_dump_json(
            indent=2,
        )


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


T = TypeVar("T", bound=BaseTool)


class NextStepToolStub(ReasoningTool, ABC):
    """SGR Core - Determines next reasoning step with adaptive planning, choosing appropriate tool
    (!) Stub class for correct autocomplete. Use NextStepToolsBuilder"""

    function: T = Field(description="Select the appropriate tool for the next step")


class DiscriminantToolMixin(BaseModel):
    tool_name_discriminator: str = Field(..., description="Tool name discriminator")

    def model_dump(self, *args, **kwargs):
        # it could cause unexpected field issues if not excluded
        exclude = kwargs.pop("exclude", set())
        exclude = exclude.union({"tool_name_discriminator"})
        return super().model_dump(*args, exclude=exclude, **kwargs)


class NextStepToolsBuilder:
    """SGR Core - Builder for NextStepTool with dynamic union tool function type on
    pydantic models level."""

    @classmethod
    def _create_discriminant_tool(cls, tool_class: Type[T]) -> Type[BaseModel]:
        """Create discriminant version of tool with tool_name as instance
        field."""

        return create_model(  # noqa
            f"D_{tool_class.__name__}",
            __base__=(tool_class, DiscriminantToolMixin),  # the order matters here
            tool_name_discriminator=(Literal[tool_class.tool_name], Field(..., description="Tool name discriminator")),
        )

    @classmethod
    def _create_tool_types_union(cls, tools_list: list[Type[T]]) -> Type:
        """Create discriminated union of tools."""
        if len(tools_list) == 1:
            return cls._create_discriminant_tool(tools_list[0])
        # SGR inference struggles with choosing right schema otherwise
        discriminant_tools = [cls._create_discriminant_tool(tool) for tool in tools_list]
        union = reduce(operator.or_, discriminant_tools)
        return Annotated[union, Field()]

    @classmethod
    def build_NextStepTools(cls, tools_list: list[Type[T]]) -> Type[NextStepToolStub]:  # noqa
        return create_model(
            "NextStepTools",
            __base__=NextStepToolStub,
            function=(cls._create_tool_types_union(tools_list), Field()),
        )


system_agent_tools = [
    ClarificationTool,
    GeneratePlanTool,
    AdaptPlanTool,
    FinalAnswerTool,
    ReasoningTool,
]
