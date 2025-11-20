import json
import logging
import os
import traceback
import uuid
from datetime import datetime
from typing import Type

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionFunctionToolParam

from sgr_deep_research.core.agent_definition import AgentConfig
from sgr_deep_research.core.models import AgentStatesEnum, ResearchContext
from sgr_deep_research.core.services.prompt_loader import PromptLoader
from sgr_deep_research.core.services.registry import AgentRegistry
from sgr_deep_research.core.stream import OpenAIStreamingGenerator
from sgr_deep_research.core.tools import (
    BaseTool,
    ClarificationTool,
    ReasoningTool,
)


class AgentRegistryMixin:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.__name__ not in ("BaseAgent",):
            AgentRegistry.register(cls, name=cls.name)


class BaseAgent(AgentRegistryMixin):
    """Base class for agents."""

    name: str = "base_agent"

    def __init__(
        self,
        task: str,
        openai_client: AsyncOpenAI,
        agent_config: AgentConfig,
        toolkit: list[Type[BaseTool]],
        def_name: str | None = None,
        **kwargs: dict,
    ):
        self.id = f"{def_name or self.name}_{uuid.uuid4()}"
        self.openai_client = openai_client
        self.config = agent_config
        self.creation_time = datetime.now()
        self.task = task
        self.toolkit = toolkit

        self._context = ResearchContext()
        self.conversation = []

        self.streaming_generator = OpenAIStreamingGenerator(model=self.id)
        self.logger = logging.getLogger(f"sgr_deep_research.agents.{self.id}")
        self.log = []

    async def provide_clarification(self, clarifications: str):
        """Receive clarification from an external source (e.g. user input)"""
        self.conversation.append(
            {"role": "user", "content": PromptLoader.get_clarification_template(clarifications, self.config.prompts)}
        )
        self._context.clarifications_used += 1
        self._context.clarification_received.set()
        self._context.state = AgentStatesEnum.RESEARCHING
        self.logger.info(f"✅ Clarification received: {clarifications[:2000]}...")

    def _log_reasoning(self, result: ReasoningTool) -> None:
        next_step = result.remaining_steps[0] if result.remaining_steps else "Completing"
        self.logger.info(
            f"""
    ###############################################
    🤖 LLM RESPONSE DEBUG:
       🧠 Reasoning Steps: {result.reasoning_steps}
       📊 Current Situation: '{result.current_situation[:400]}...'
       📋 Plan Status: '{result.plan_status[:400]}...'
       🔍 Searches Done: {self._context.searches_used}
       🔍 Clarifications Done: {self._context.clarifications_used}
       ✅ Enough Data: {result.enough_data}
       📝 Remaining Steps: {result.remaining_steps}
       🏁 Task Completed: {result.task_completed}
       ➡️ Next Step: {next_step}
    ###############################################"""
        )
        self.log.append(
            {
                "step_number": self._context.iteration,
                "timestamp": datetime.now().isoformat(),
                "step_type": "reasoning",
                "agent_reasoning": result.model_dump(),
            }
        )

    def _log_tool_execution(self, tool: BaseTool, result: str):
        self.logger.info(
            f"""
###############################################
🛠️ TOOL EXECUTION DEBUG:
    🔧 Tool Name: {tool.tool_name}
    📋 Tool Model: {tool.model_dump_json(indent=2)}
    🔍 Result: '{result[:400]}...'
###############################################"""
        )
        self.log.append(
            {
                "step_number": self._context.iteration,
                "timestamp": datetime.now().isoformat(),
                "step_type": "tool_execution",
                "tool_name": tool.tool_name,
                "agent_tool_context": tool.model_dump(),
                "agent_tool_execution_result": result,
            }
        )

    def _save_agent_log(self):
        from sgr_deep_research.core.agent_config import GlobalConfig

        logs_dir = GlobalConfig().execution.logs_dir
        os.makedirs(logs_dir, exist_ok=True)
        filepath = os.path.join(logs_dir, f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{self.id}-log.json")
        agent_log = {
            "id": self.id,
            "model_config": self.config.llm.model_dump(
                exclude={"api_key", "proxy"}
            ),  # Sensitive data excluded by default
            "task": self.task,
            "toolkit": [tool.tool_name for tool in self.toolkit],
            "log": self.log,
        }

        json.dump(agent_log, open(filepath, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    async def _prepare_context(self) -> list[dict]:
        """Prepare conversation context with system prompt."""
        return [
            {"role": "system", "content": PromptLoader.get_system_prompt(self.toolkit, self.config.prompts)},
            {
                "role": "user",
                "content": PromptLoader.get_initial_user_request(self.task, self.config.prompts),
            },
            *self.conversation,
        ]

    async def _prepare_tools(self) -> list[ChatCompletionFunctionToolParam]:
        """Prepare available tools for the current agent state and progress."""
        raise NotImplementedError("_prepare_tools must be implemented by subclass")

    async def _reasoning_phase(self) -> ReasoningTool:
        """Call LLM to decide next action based on current context."""
        raise NotImplementedError("_reasoning_phase must be implemented by subclass")

    async def _select_action_phase(self, reasoning: ReasoningTool) -> BaseTool:
        """Select the most suitable tool for the action decided in the
        reasoning phase.

        Returns the tool suitable for the action.
        """
        raise NotImplementedError("_select_action_phase must be implemented by subclass")

    async def _action_phase(self, tool: BaseTool) -> str:
        """Call Tool for the action decided in the select_action phase.

        Returns string or dumped JSON result of the tool execution.
        """
        raise NotImplementedError("_action_phase must be implemented by subclass")

    async def execute(
        self,
    ):
        self.logger.info(f"🚀 Starting for task: '{self.task}'")
        try:
            while self._context.state not in AgentStatesEnum.FINISH_STATES.value:
                self._context.iteration += 1
                self.logger.info(f"Step {self._context.iteration} started")

                reasoning = await self._reasoning_phase()
                self._context.current_step_reasoning = reasoning
                action_tool = await self._select_action_phase(reasoning)
                await self._action_phase(action_tool)

                if isinstance(action_tool, ClarificationTool):
                    self.logger.info("\n⏸️  Research paused - please answer questions")
                    self._context.state = AgentStatesEnum.WAITING_FOR_CLARIFICATION
                    self.streaming_generator.finish()
                    self._context.clarification_received.clear()
                    await self._context.clarification_received.wait()
                    continue

        except Exception as e:
            self.logger.error(f"❌ Agent execution error: {str(e)}")
            self._context.state = AgentStatesEnum.FAILED
            traceback.print_exc()
        finally:
            if self.streaming_generator is not None:
                self.streaming_generator.finish(self._context.execution_result)
            self._save_agent_log()
