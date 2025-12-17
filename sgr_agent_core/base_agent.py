import json
import logging
import os
import traceback
import uuid
from datetime import datetime
from typing import Type

from openai import AsyncOpenAI, pydantic_function_tool
from openai.types.chat import ChatCompletionFunctionToolParam

from sgr_agent_core.agent_definition import AgentConfig
from sgr_agent_core.models import AgentContext, AgentStatesEnum
from sgr_agent_core.services.prompt_loader import PromptLoader
from sgr_agent_core.services.registry import AgentRegistry
from sgr_agent_core.stream import OpenAIStreamingGenerator
from sgr_agent_core.tools import (
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

        self._context = AgentContext()
        self.conversation = []

        self.streaming_generator = OpenAIStreamingGenerator(model=self.id)
        self.logger = logging.getLogger(f"sgr_agent_core.agents.{self.id}")
        self.log = []
        
        # Метрики токенов и производительности
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        self.llm_call_count = 0

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

    def _log_llm_call(self, phase: str, request_data: dict, response_data: dict, duration_ms: float = 0):
        """Логирование полного запроса и ответа LLM для трейсинга.
        
        Args:
            phase: Название фазы (reasoning, action_selection, etc.)
            request_data: Полный запрос к LLM (messages, tools, parameters)
            response_data: Полный ответ от LLM
            duration_ms: Длительность запроса в миллисекундах
        """
        # Извлекаем метрики использования токенов
        usage = response_data.get('usage') or {}
        prompt_tokens = usage.get('prompt_tokens', 0) if isinstance(usage, dict) else 0
        completion_tokens = usage.get('completion_tokens', 0) if isinstance(usage, dict) else 0
        total_tokens_call = usage.get('total_tokens', 0) if isinstance(usage, dict) else 0
        
        # Обновляем кумулятивные счетчики
        if self.config.execution.track_token_usage:
            self.total_prompt_tokens += prompt_tokens
            self.total_completion_tokens += completion_tokens
            self.total_tokens += total_tokens_call
            self.llm_call_count += 1
        
        # Вычисляем скорость
        tokens_per_second = (completion_tokens / (duration_ms / 1000)) if duration_ms > 0 else 0
        
        self.logger.info(
            f"""
###############################################
🤖 LLM API CALL - {phase.upper()}
    📤 REQUEST:
        Model: {request_data.get('model')}
        Temperature: {request_data.get('temperature')}
        Max Tokens: {request_data.get('max_tokens')}
        Messages Count: {len(request_data.get('messages', []))}
        Tools Count: {len(request_data.get('tools', []))}
    📥 RESPONSE:
        Finish Reason: {response_data.get('choices', [{}])[0].get('finish_reason')}
        Tool Calls: {len(response_data.get('choices', [{}])[0].get('message', {}).get('tool_calls', []))}
    📊 МЕТРИКИ:
        ⏱️  Время ответа: {duration_ms:.0f}ms
        🔢 Токены (prompt): {prompt_tokens}
        💬 Токены (completion): {completion_tokens}
        📈 Всего токенов: {total_tokens_call}
        ⚡ Скорость: {tokens_per_second:.1f} tok/s
    📊 КУМУЛЯТИВНЫЕ:
        🔢 Всего prompt токенов: {self.total_prompt_tokens}
        💬 Всего completion токенов: {self.total_completion_tokens}
        📈 Общий расход токенов: {self.total_tokens}
        🔄 Вызовов LLM: {self.llm_call_count}
###############################################"""
        )
        
        # Сохраняем полный запрос и ответ
        log_entry = {
            "step_number": self._context.iteration,
            "timestamp": datetime.now().isoformat(),
            "step_type": "llm_call",
            "phase": phase,
            "request": request_data,  # Полный запрос
            "response": response_data,  # Полный ответ
        }
        
        # Добавляем метрики, если включено отслеживание
        if self.config.execution.track_token_usage:
            log_entry["metrics"] = {
                "duration_ms": duration_ms,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens_call,
                "tokens_per_second": tokens_per_second,
                "cumulative_prompt_tokens": self.total_prompt_tokens,
                "cumulative_completion_tokens": self.total_completion_tokens,
                "cumulative_total_tokens": self.total_tokens,
                "llm_call_number": self.llm_call_count,
            }
        
        self.log.append(log_entry)

    def _save_agent_log(self):
        from sgr_agent_core.agent_config import GlobalConfig

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
        
        # Добавляем финальную сводку по токенам
        if self.config.execution.track_token_usage:
            agent_log["token_usage_summary"] = {
                "total_prompt_tokens": self.total_prompt_tokens,
                "total_completion_tokens": self.total_completion_tokens,
                "total_tokens": self.total_tokens,
                "llm_calls_count": self.llm_call_count,
            }

        json.dump(agent_log, open(filepath, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    async def _prepare_context(self) -> list[dict]:
        """Prepare a conversation context with system prompt, task data and any
        other context. Override this method to change the context setup for the
        agent.

        Returns a list of dictionaries, each containing a role and
        content key.
        """
        return [
            {"role": "system", "content": PromptLoader.get_system_prompt(self.toolkit, self.config.prompts)},
            {
                "role": "user",
                "content": PromptLoader.get_initial_user_request(self.task, self.config.prompts),
            },
            *self.conversation,
        ]

    async def _prepare_tools(self) -> list[ChatCompletionFunctionToolParam]:
        """Prepare available tools for the current agent state and progress.
        Override this method to change the tool setup or conditions for tool
        usage.

        Returns a list of ChatCompletionFunctionToolParam based
        available tools.
        """
        tools = set(self.toolkit)
        if self._context.iteration >= self.config.execution.max_iterations:
            raise RuntimeError("Max iterations reached")
        return [pydantic_function_tool(tool, name=tool.tool_name) for tool in tools]

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
            return self._context.execution_result

        except Exception as e:
            self.logger.error(f"❌ Agent execution error: {str(e)}")
            self._context.state = AgentStatesEnum.FAILED
            traceback.print_exc()
        finally:
            if self.streaming_generator is not None:
                self.streaming_generator.finish(self._context.execution_result)
            self._save_agent_log()
