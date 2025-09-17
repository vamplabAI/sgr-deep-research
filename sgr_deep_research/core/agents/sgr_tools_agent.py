import logging
import uuid
from typing import Literal, Type

from openai import pydantic_function_tool
from openai.types.chat import ChatCompletionFunctionToolParam

from sgr_deep_research.core.agents.no_need_now.sgr_agent import SGRResearchAgent
from sgr_deep_research.core.tools import (
    AgentCompletionTool,
    BaseTool,
    ClarificationTool,
    CreateReportTool,
    ReasoningTool,
    WebSearchTool,
    research_agent_tools,
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


class SGRToolCallingResearchAgent(SGRResearchAgent):
    """Agent that uses OpenAI native function calling to select and execute
    tools based on SGR like reasoning scheme."""

    def __init__(
        self,
        task: str,
        toolkit: list[Type[BaseTool]] | None = None,
        max_clarifications: int = 3,
        max_searches: int = 4,
        max_iterations: int = 10,
        use_streaming: bool = True,
    ):
        super().__init__(
            task=task,
            toolkit=toolkit,
            max_clarifications=max_clarifications,
            max_iterations=max_iterations,
            max_searches=max_searches,
            use_streaming=use_streaming,
        )
        self.id = f"sgr_tool_calling_agent_{uuid.uuid4()}"
        self.toolkit = [*system_agent_tools, *research_agent_tools, *(toolkit if toolkit else [])]
        self.tool_choice: Literal["required"] = "required"

    async def _prepare_tools(self) -> list[ChatCompletionFunctionToolParam]:
        """Prepare available tools for current agent state and progress."""
        tools = set(self.toolkit)
        if self._context.iteration >= self.max_iterations:
            tools = [
                ReasoningTool,
                CreateReportTool,
                AgentCompletionTool,
            ]
        if self._context.clarifications_used >= self.max_clarifications:
            tools -= {
                ClarificationTool,
            }
        if self._context.searches_used >= self.max_searches:
            tools -= {
                WebSearchTool,
            }
        return [pydantic_function_tool(tool, name=tool.tool_name, description=tool.description) for tool in tools]

    async def _reasoning_phase(self) -> ReasoningTool:
        # Получаем параметры модели с учетом deep_level
        context_messages = await self._prepare_context()
        # Сохраняем приблизительную длину промпта для оценки токенов
        self._last_prompt_length = sum(len(str(msg.get('content', ''))) for msg in context_messages)
        
        model_params = self._get_model_parameters(getattr(self, '_deep_level', 0))
        model_params.update({
            "messages": context_messages,
            "tools": await self._prepare_tools(),
            "tool_choice": {"type": "function", "function": {"name": ReasoningTool.tool_name}},
        })
        
        if self.use_streaming:
            # Streaming режим (для API)
            usage_data = None
            async with self.openai_client.chat.completions.stream(**model_params) as stream:
                async for event in stream:
                    if event.type == "chunk":
                        content = event.chunk.choices[0].delta.content
                        self.streaming_generator.add_chunk(content)
                        # Попытаемся получить usage из chunk, если доступно
                        if hasattr(event.chunk, 'usage') and event.chunk.usage:
                            usage_data = event.chunk.usage
                final_completion = await stream.get_final_completion()
                # Если usage не было получено из chunk, попробуем из final completion
                if not usage_data and final_completion.usage:
                    usage_data = final_completion.usage
                self.metrics.add_api_call(usage_data)
                reasoning: ReasoningTool = (
                    final_completion.choices[0].message.tool_calls[0].function.parsed_arguments
                )
        else:
            # Non-streaming режим (для CLI) - получаем точные данные о токенах
            completion = await self.openai_client.chat.completions.create(**model_params)
            self.metrics.add_api_call(completion.usage)
            # В non-streaming режиме нужно парсить arguments вручную
            import json
            arguments_str = completion.choices[0].message.tool_calls[0].function.arguments
            arguments_dict = json.loads(arguments_str)
            reasoning: ReasoningTool = ReasoningTool(**arguments_dict)
        self.conversation.append(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "type": "function",
                        "id": f"{self._context.iteration}-reasoning",
                        "function": {
                            "name": reasoning.tool_name,
                            "arguments": reasoning.model_dump_json(),
                        },
                    }
                ],
            }
        )
        tool_call_result = reasoning(self._context)
        self.conversation.append(
            {"role": "tool", "content": tool_call_result, "tool_call_id": f"{self._context.iteration}-reasoning"}
        )
        self._log_reasoning(reasoning)
        return reasoning

    async def _select_action_phase(self, reasoning: ReasoningTool) -> BaseTool:
        # Получаем параметры модели с учетом deep_level
        context_messages = await self._prepare_context()
        # Сохраняем приблизительную длину промпта для оценки токенов  
        self._last_prompt_length = sum(len(str(msg.get('content', ''))) for msg in context_messages)
        
        model_params = self._get_model_parameters(getattr(self, '_deep_level', 0))
        model_params.update({
            "messages": context_messages,
            "tools": await self._prepare_tools(),
            "tool_choice": self.tool_choice,
        })
        
        if self.use_streaming:
            # Streaming режим (для API)
            usage_data = None
            async with self.openai_client.chat.completions.stream(**model_params) as stream:
                async for event in stream:
                    if event.type == "chunk":
                        content = event.chunk.choices[0].delta.content
                        self.streaming_generator.add_chunk(content)
                        # Попытаемся получить usage из chunk, если доступно
                        if hasattr(event.chunk, 'usage') and event.chunk.usage:
                            usage_data = event.chunk.usage
            final_completion = await stream.get_final_completion()
            # Если usage не было получено из chunk, попробуем из final completion
            if not usage_data and final_completion.usage:
                usage_data = final_completion.usage
            self.metrics.add_api_call(usage_data)
            tool = final_completion.choices[0].message.tool_calls[0].function.parsed_arguments
        else:
            # Non-streaming режим (для CLI) - получаем точные данные о токенов
            completion = await self.openai_client.chat.completions.create(**model_params)
            self.metrics.add_api_call(completion.usage)
            # В non-streaming режиме нужно парсить arguments вручную
            import json
            tool_name = completion.choices[0].message.tool_calls[0].function.name
            arguments_str = completion.choices[0].message.tool_calls[0].function.arguments
            arguments_dict = json.loads(arguments_str)
            
            # Простой маппинг имен инструментов к классам
            tool_class = None
            for tool_cls in self.toolkit:
                if hasattr(tool_cls, 'tool_name') and tool_cls.tool_name == tool_name:
                    tool_class = tool_cls
                    break
            
            if not tool_class:
                raise ValueError(f"Tool class not found for tool name: {tool_name}")
            
            tool = tool_class(**arguments_dict)

        if not isinstance(tool, BaseTool):
            raise ValueError("Selected tool is not a valid BaseTool instance")
        self.conversation.append(
            {
                "role": "assistant",
                "content": reasoning.remaining_steps[0] if reasoning.remaining_steps else "Completing",
                "tool_calls": [
                    {
                        "type": "function",
                        "id": f"{self._context.iteration}-action",
                        "function": {
                            "name": tool.tool_name,
                            "arguments": tool.model_dump_json(),
                        },
                    }
                ],
            }
        )
        self.streaming_generator.add_tool_call(
            f"{self._context.iteration}-action", tool.tool_name, tool.model_dump_json()
        )
        return tool
