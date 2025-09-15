import json
import logging
import os
import traceback
import uuid
from datetime import datetime
from typing import Type

import httpx
from openai import AsyncOpenAI, AsyncAzureOpenAI
from openai.types.chat import ChatCompletionFunctionToolParam

from sgr_deep_research.core.models import AgentStatesEnum, ResearchContext
from sgr_deep_research.core.prompts import PromptLoader
from sgr_deep_research.core.stream import OpenAIStreamingGenerator
from sgr_deep_research.core.tools import (
    # Base
    BaseTool,
    ClarificationTool,
    ReasoningTool,
    system_agent_tools,
)
from sgr_deep_research.settings import get_config

logging.basicConfig(
    level=logging.INFO,
    encoding="utf-8",
    format="%(asctime)s - %(name)s - %(lineno)d - %(levelname)s -  - %(message)s",
    handlers=[logging.StreamHandler()],
)

config = get_config()
logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for agents."""

    def __init__(
        self,
        task: str,
        toolkit: list[Type[BaseTool]] | None = None,
        max_iterations: int = 10,
        max_clarifications: int = 3,
    ):
        self.id = f"base_agent_{uuid.uuid4()}"
        self.task = task
        self.toolkit = [*system_agent_tools, *(toolkit or [])]

        self._context = ResearchContext()
        self.conversation = []
        self.log = []
        self.max_iterations = max_iterations
        self.max_clarifications = max_clarifications

        # Initialize OpenAI client based on configuration
        if config.azure:
            # Azure OpenAI configuration
            client_kwargs = {
                "azure_endpoint": config.azure.base_url,
                "api_key": config.azure.api_key,
                "api_version": config.azure.api_version,
            }
            if config.azure.proxy.strip():
                client_kwargs["http_client"] = httpx.AsyncClient(proxy=config.azure.proxy)
            self.openai_client = AsyncAzureOpenAI(**client_kwargs)
            self.model_name = config.azure.deployment_name
            self.max_tokens = config.azure.max_tokens
            self.max_completion_tokens = config.azure.max_completion_tokens
            self.temperature = config.azure.temperature
            self.reasoning_effort = config.azure.reasoning_effort
            self.verbosity = config.azure.verbosity
        elif config.openai:
            # Standard OpenAI configuration
            client_kwargs = {"base_url": config.openai.base_url, "api_key": config.openai.api_key}
            if config.openai.proxy.strip():
                client_kwargs["http_client"] = httpx.AsyncClient(proxy=config.openai.proxy)
            self.openai_client = AsyncOpenAI(**client_kwargs)
            self.model_name = config.openai.model
            self.max_tokens = config.openai.max_tokens
            self.max_completion_tokens = config.openai.max_completion_tokens
            self.temperature = config.openai.temperature
            self.reasoning_effort = config.openai.reasoning_effort
            self.verbosity = config.openai.verbosity
        else:
            raise ValueError("Either 'openai' or 'azure' configuration must be provided")
        self.streaming_generator = OpenAIStreamingGenerator(model=self.id)

    def _get_model_parameters(self, deep_level: int = 0) -> dict:
        """Get model parameters based on model type and deep level."""
        params = {
            "model": self.model_name,
        }
        
        # Определяем, поддерживает ли модель новые параметры GPT-5
        is_gpt5 = "gpt-5" in self.model_name.lower() or "o3" in self.model_name.lower()
        
        if is_gpt5:
            # GPT-5 не поддерживает кастомную температуру, только дефолтную (1)
            # params["temperature"] = 1  # Можно не указывать, используется по умолчанию
            
            # GPT-5 и новые модели используют max_completion_tokens
            base_tokens = self.max_completion_tokens
            params["max_completion_tokens"] = min(base_tokens * (deep_level + 1), 128000)  # До 128K
            
            # Специальные параметры GPT-5
            if deep_level >= 2:
                params["reasoning_effort"] = "high"  # Максимальное рассуждение для deep режимов
                params["verbosity"] = "high"  # Максимальная подробность
            elif deep_level >= 1:
                params["reasoning_effort"] = "medium"
                params["verbosity"] = "medium"
            else:
                params["reasoning_effort"] = self.reasoning_effort
                params["verbosity"] = self.verbosity
        else:
            # Старые модели поддерживают температуру и используют max_tokens
            params["temperature"] = self.temperature
            base_tokens = self.max_tokens
            params["max_tokens"] = min(base_tokens * (deep_level + 1), 128000)  # До 128K для GPT-4
        
        return params

    async def provide_clarification(self, clarifications: str):
        """Receive clarification from external source (e.g. user input)"""
        self.conversation.append({"role": "user", "content": f"CLARIFICATIONS: {clarifications}"})
        self._context.clarifications_used += 1
        self._context.clarification_received.set()
        self._context.state = AgentStatesEnum.RESEARCHING
        logger.info(f"✅ Clarification received: {clarifications[:2000]}...")

    def _log_reasoning(self, result: ReasoningTool) -> None:
        next_step = result.remaining_steps[0] if result.remaining_steps else "Completing"
        logger.info(
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
        logger.info(
            f"🛠️  Tool Execution Result:\n"
            f"   🔧 Tool: {tool.tool_name}\n"
            f"   📄 Result Preview: '{result[:3000]}...'\n"
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
        logs_dir = config.execution.logs_dir
        os.makedirs(logs_dir, exist_ok=True)
        filepath = os.path.join(logs_dir, f"{self.id}-log.json")
        agent_log = {
            "id": self.id,
            "task": self.task,
            "context": self._context.agent_state(),
            "log": self.log,
        }

        json.dump(agent_log, open(filepath, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    async def _prepare_context(self) -> list[dict]:
        """Prepare conversation context with system prompt."""
        deep_level = getattr(self, '_deep_level', 0)
        system_prompt = PromptLoader.get_system_prompt(
            user_request=self.task, 
            sources=list(self._context.sources.values()),
            deep_level=deep_level
        )
        # Заменяем плейсхолдеры для счетчиков
        system_prompt = system_prompt.replace(
            "{searches_count}", str(self._context.searches_used)
        ).replace(
            "{max_searches}", str(getattr(self, 'max_searches', 10))
        )
        return [{"role": "system", "content": system_prompt}, *self.conversation]

    async def _prepare_tools(self) -> list[ChatCompletionFunctionToolParam]:
        """Prepare available tools for current agent state and progress."""
        raise NotImplementedError("_prepare_tools must be implemented by subclass")

    async def _reasoning_phase(self) -> ReasoningTool:
        """Call LLM to decide next action based on current context."""
        raise NotImplementedError("_reasoning_phase must be implemented by subclass")

    async def _select_action_phase(self, reasoning: ReasoningTool) -> BaseTool:
        """Select most suitable tool for the action decided in reasoning phase.

        Returns the tool suitable for the action.
        """
        raise NotImplementedError("_select_action_phase must be implemented by subclass")

    async def _action_phase(self, tool: BaseTool) -> str:
        """Call Tool for the action decided in select_action phase.

        Returns string or dumped json result of the tool execution.
        """
        raise NotImplementedError("_action_phase must be implemented by subclass")

    async def execute(
        self,
    ):
        logger.info(f"🚀 Starting agent {self.id} for task: '{self.task}'")
        self.conversation.extend(
            [
                {
                    "role": "user",
                    "content": f"\nORIGINAL USER REQUEST: '{self.task}'\n",
                }
            ]
        )
        try:
            while self._context.state not in AgentStatesEnum.FINISH_STATES.value:
                self._context.iteration += 1
                logger.info(f"agent {self.id} Step {self._context.iteration} started")

                reasoning = await self._reasoning_phase()
                self._context.current_state_reasoning = reasoning
                action_tool = await self._select_action_phase(reasoning)
                action_result = await self._action_phase(action_tool)

                if isinstance(action_tool, ClarificationTool):
                    logger.info("\n⏸️  Research paused - please answer questions")
                    logger.info(action_result)
                    self._context.state = AgentStatesEnum.WAITING_FOR_CLARIFICATION
                    self._context.clarification_received.clear()
                    await self._context.clarification_received.wait()
                    continue

        except Exception as e:
            logger.error(f"❌ Agent execution error: {str(e)}")
            self._context.state = AgentStatesEnum.FAILED
            traceback.print_exc()
        finally:
            self.streaming_generator.finish()
            self._save_agent_log()
