import json
import logging
import os
import traceback
import uuid
from datetime import datetime
from typing import Type

from openai import AsyncOpenAI
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam

from sgr_deep_research.core.agent_definition import ExecutionConfig, LLMConfig, PromptsConfig
from sgr_deep_research.core.base_agent import BaseAgent
from sgr_deep_research.gigachat_compatability.models import AgentStatesEnum, ResearchContextCounted
from sgr_deep_research.core.services.prompt_loader import PromptLoader
from sgr_deep_research.core.services.registry import AgentRegistry
from sgr_deep_research.core.stream import OpenAIStreamingGenerator
from sgr_deep_research.gigachat_compatability.base_tool import BaseTool_functional
from sgr_deep_research.gigachat_compatability.tools.clarification_tool import ClarificationTool_functional
from sgr_deep_research.gigachat_compatability.tools.reasoning_tool import ReasoningTool_functional


class AgentRegistryMixin:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.__name__ not in ("BaseAgent_functional",):
            AgentRegistry.register(cls, name=cls.name)


class BaseAgent_functional(BaseAgent, AgentRegistryMixin):
    """Base class for agents."""

    name: str = "base_agent"

    def __init__(
        self,
        task: str,
        openai_client: AsyncOpenAI,
        llm_config: LLMConfig,
        prompts_config: PromptsConfig,
        execution_config: ExecutionConfig,
        toolkit: list[Type[BaseTool_functional]] | None = None,
        **kwargs: dict,
    ):
        self.id = f"{self.name}_{uuid.uuid4()}"
        self.logger = logging.getLogger(f"sgr_deep_research.agents.{self.id}")
        self.creation_time = datetime.now()
        self.task = task
        self.toolkit = toolkit or []

        self._context = ResearchContextCounted()
        self.conversation = []
        self.log = []
        self.max_iterations = execution_config.max_iterations
        self.max_clarifications = execution_config.max_clarifications

        self.openai_client = openai_client
        self.llm_config = llm_config
        self.prompts_config = prompts_config

        self.streaming_generator = OpenAIStreamingGenerator(model=self.id)

    async def provide_clarification(self, clarifications: str):
        """Receive clarification from external source (e.g. user input)"""
        self.conversation.append(
            {"role": "user", "content": PromptLoader.get_clarification_template(clarifications, self.prompts_config)}
        )
        self._context.clarifications_used += 1
        self._context.clarification_received.set()
        self._context.state = AgentStatesEnum.RESEARCHING
        self.logger.info(f"✅ Clarification received: {clarifications[:2000]}...")

    def _accumulate_tokens(self, usage) -> None:
        """Store token usage reported by the LLM response."""
        if usage is None:
            return
        total_tokens = getattr(usage, "total_tokens", None)
        if total_tokens is None and isinstance(usage, dict):
            total_tokens = usage.get("total_tokens")
        if total_tokens is None:
            return
        self._context.tokens_used += total_tokens

    def _log_reasoning(self, result: ReasoningTool_functional) -> None:
        next_step = result.remaining_steps[0] if result.remaining_steps else "Completing"
        self.logger.info(
            f"""
###############################################
 REASONING DEBUG:
    Reasoning Steps: {result.reasoning_steps}
    Current Situation: '{result.current_situation[:400]}...'
    Plan Status: '{result.plan_status[:400]}...'
    Searches Done: {self._context.searches_used}
    Clarifications Done: {self._context.clarifications_used}
    Enough Data: {result.enough_data}
    Remaining Steps: {result.remaining_steps}
    Task Completed: {result.task_completed}
   ➡ Next Step: {next_step}
    Total tokens burned: {self._context.tokens_used}
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

    def _log_tool_execution(self, tool: BaseTool_functional, result: str):
        tool_name = tool.tool_name if tool is not None else "Unchosen"
        tool_model = tool.model_dump_json(indent=2) if tool is not None else {"error": result}
        self.logger.info(
            f"""
###############################################
🛠️ TOOL EXECUTION DEBUG:
    Tool Name: {tool_name}
    Tool Model: {tool_model}
    Result: '{result[:400]}...'
    Total tokens burned: {self._context.tokens_used}
###############################################"""
        )
        self.log.append(
            {
                "step_number": self._context.iteration,
                "timestamp": datetime.now().isoformat(),
                "step_type": "tool_execution",
                "tool_name": tool_name,
                "agent_tool_context": tool_model,
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
            "model_config": self.llm_config.model_dump(exclude={"api_key", "proxy"}),
            "task": self.task,
            "toolkit": [tool.tool_name for tool in self.toolkit],
            "log": self.log,
        }

        json.dump(agent_log, open(filepath, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    async def _prepare_context(self) -> list[dict]:
        """Prepare conversation context with system prompt."""
        return [
            {"role": "system", "content": PromptLoader.get_system_prompt(self.toolkit, self.prompts_config)},
            *self.conversation,
        ]

    async def _prepare_tools(self) -> list[ChatCompletionToolParam]:
        """Prepare available tools for current agent state and progress."""
        raise NotImplementedError("_prepare_tools must be implemented by subclass")

    async def _reasoning_phase(self) -> ReasoningTool_functional | None:
        """Call LLM to decide next action based on current context."""
        raise NotImplementedError("_reasoning_phase must be implemented by subclass")

    async def _select_action_phase(self, reasoning: ReasoningTool_functional) -> BaseTool_functional:
        """Select most suitable tool for the action decided in reasoning phase.

        Returns the tool suitable for the action.
        """
        raise NotImplementedError("_select_action_phase must be implemented by subclass")

    async def _action_phase(self, tool: BaseTool_functional) -> str:
        """Call Tool for the action decided in select_action phase.

        Returns string or dumped json result of the tool execution.
        """
        raise NotImplementedError("_action_phase must be implemented by subclass")

    async def execute(
        self,
    ):
        self.logger.info(f"🚀 Starting for task: '{self.task}'")
        self.conversation.extend(
            [
                {
                    "role": "user",
                    "content": PromptLoader.get_initial_user_request(self.task, self.prompts_config),
                }
            ]
        )
        try:
            while self._context.state not in AgentStatesEnum.FINISH_STATES.value:
                self._context.iteration += 1
                self.logger.info(f"Step {self._context.iteration} started")

                reasoning = await self._reasoning_phase()
                self._context.current_step_reasoning = reasoning
                action_tool = await self._select_action_phase(reasoning)
                await self._action_phase(action_tool)

                if isinstance(action_tool, ClarificationTool_functional):
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
            # if self.streaming_generator is not None:
            #     self.streaming_generator.finish()
            self._save_agent_log()
