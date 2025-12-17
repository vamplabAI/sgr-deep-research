import time
from typing import Literal, Type

from openai import AsyncOpenAI, pydantic_function_tool
from openai.types.chat import ChatCompletionFunctionToolParam

from sgr_agent_core.agent_config import AgentConfig
from sgr_agent_core.agents.sgr_agent import SGRAgent
from sgr_agent_core.models import AgentStatesEnum
from sgr_agent_core.tools import (
    BaseTool,
    ClarificationTool,
    CreateReportTool,
    ExtractPageContentTool,
    FinalAnswerTool,
    ReasoningTool,
    WebSearchTool,
)


class SGRToolCallingAgent(SGRAgent):
    """Agent that uses OpenAI native function calling to select and execute
    tools based on SGR like a reasoning scheme."""

    name: str = "sgr_tool_calling_agent"

    def __init__(
        self,
        task: str,
        openai_client: AsyncOpenAI,
        agent_config: AgentConfig,
        toolkit: list[Type[BaseTool]],
        def_name: str | None = None,
        **kwargs: dict,
    ):
        super().__init__(
            task=task,
            openai_client=openai_client,
            agent_config=agent_config,
            toolkit=toolkit,
            def_name=def_name,
            **kwargs,
        )
        self.tool_choice: Literal["required"] = "required"

    async def _reasoning_phase(self) -> ReasoningTool:
        # Подготавливаем данные запроса
        messages = await self._prepare_context()
        tools = [pydantic_function_tool(ReasoningTool, name=ReasoningTool.tool_name)]
        tool_choice_param = {"type": "function", "function": {"name": ReasoningTool.tool_name}}
        
        # Засекаем время начала
        start_time = time.time()
        
        if self.config.execution.enable_streaming:
            # РЕЖИМ СТРИМИНГА
            request_data = {
                "model": self.config.llm.model,
                "messages": messages,
                "max_tokens": self.config.llm.max_tokens,
                "temperature": self.config.llm.temperature,
                "tools": tools,
                "tool_choice": tool_choice_param,
                "stream": True,
                "stream_options": {"include_usage": True},
            }
            
            async with self.openai_client.chat.completions.stream(
                model=self.config.llm.model,
                messages=messages,
                max_tokens=self.config.llm.max_tokens,
                temperature=self.config.llm.temperature,
                tools=tools,
                tool_choice=tool_choice_param,
                stream_options={"include_usage": True},
            ) as stream:
                async for event in stream:
                    if event.type == "chunk":
                        self.streaming_generator.add_chunk(event.chunk)
                
                final_completion = await stream.get_final_completion()
                reasoning: ReasoningTool = (
                    final_completion.choices[0].message.tool_calls[0].function.parsed_arguments
                )
        else:
            # РЕЖИМ БЕЗ СТРИМИНГА - обычный запрос
            request_data = {
                "model": self.config.llm.model,
                "messages": messages,
                "max_tokens": self.config.llm.max_tokens,
                "temperature": self.config.llm.temperature,
                "tools": tools,
                "tool_choice": tool_choice_param,
                "stream": False,
            }
            
            final_completion = await self.openai_client.chat.completions.create(
                model=self.config.llm.model,
                messages=messages,
                max_tokens=self.config.llm.max_tokens,
                temperature=self.config.llm.temperature,
                tools=tools,
                tool_choice=tool_choice_param,
            )
            
            # В обычном режиме нужно парсить arguments вручную
            import json
            tool_call = final_completion.choices[0].message.tool_calls[0]
            arguments_dict = json.loads(tool_call.function.arguments)
            reasoning: ReasoningTool = ReasoningTool(**arguments_dict)
        
        # Вычисляем время выполнения
        duration_ms = (time.time() - start_time) * 1000
        
        # Логируем LLM вызов с метриками
        response_data = final_completion.model_dump()
        self._log_llm_call("reasoning_phase", request_data, response_data, duration_ms)
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
        tool_call_result = await reasoning(self._context)
        self.streaming_generator.add_tool_call(
            f"{self._context.iteration}-reasoning", reasoning.tool_name, tool_call_result
        )
        self.conversation.append(
            {"role": "tool", "content": tool_call_result, "tool_call_id": f"{self._context.iteration}-reasoning"}
        )
        self._log_reasoning(reasoning)
        return reasoning

    async def _select_action_phase(self, reasoning: ReasoningTool) -> BaseTool:
        # Подготавливаем данные запроса
        messages = await self._prepare_context()
        tools = await self._prepare_tools()
        
        # Засекаем время начала
        start_time = time.time()
        
        if self.config.execution.enable_streaming:
            # РЕЖИМ СТРИМИНГА
            request_data = {
                "model": self.config.llm.model,
                "messages": messages,
                "max_tokens": self.config.llm.max_tokens,
                "temperature": self.config.llm.temperature,
                "tools": tools,
                "tool_choice": self.tool_choice,
                "stream": True,
                "stream_options": {"include_usage": True},
            }
            
            async with self.openai_client.chat.completions.stream(
                model=self.config.llm.model,
                messages=messages,
                max_tokens=self.config.llm.max_tokens,
                temperature=self.config.llm.temperature,
                tools=tools,
                tool_choice=self.tool_choice,
                stream_options={"include_usage": True},
            ) as stream:
                async for event in stream:
                    if event.type == "chunk":
                        self.streaming_generator.add_chunk(event.chunk)
                
                completion = await stream.get_final_completion()
        else:
            # РЕЖИМ БЕЗ СТРИМИНГА - обычный запрос
            request_data = {
                "model": self.config.llm.model,
                "messages": messages,
                "max_tokens": self.config.llm.max_tokens,
                "temperature": self.config.llm.temperature,
                "tools": tools,
                "tool_choice": self.tool_choice,
                "stream": False,
            }
            
            completion = await self.openai_client.chat.completions.create(
                model=self.config.llm.model,
                messages=messages,
                max_tokens=self.config.llm.max_tokens,
                temperature=self.config.llm.temperature,
                tools=tools,
                tool_choice=self.tool_choice,
            )
        
        # Вычисляем время выполнения
        duration_ms = (time.time() - start_time) * 1000
        
        # Логируем LLM вызов с метриками
        response_data = completion.model_dump()
        self._log_llm_call("action_selection", request_data, response_data, duration_ms)

        try:
            # Для стриминга используется parsed_arguments, для обычного запроса - парсим вручную
            tool_call = completion.choices[0].message.tool_calls[0]
            
            if hasattr(tool_call.function, 'parsed_arguments'):
                # Режим стриминга
                tool = tool_call.function.parsed_arguments
            else:
                # Режим без стриминга - парсим arguments вручную
                import json
                from sgr_agent_core.services import ToolRegistry
                
                tool_name = tool_call.function.name
                arguments_dict = json.loads(tool_call.function.arguments)
                
                # Находим класс инструмента по имени
                tool_class = ToolRegistry.get(tool_name)
                if tool_class:
                    tool = tool_class(**arguments_dict)
                else:
                    raise ValueError(f"Tool '{tool_name}' not found in registry")
                    
        except (IndexError, AttributeError, TypeError, json.JSONDecodeError) as e:
            # LLM returned a text response instead of a tool call - treat as completion
            final_content = completion.choices[0].message.content or "Task completed successfully"
            tool = FinalAnswerTool(
                reasoning="Agent decided to complete the task",
                completed_steps=[],
                answer=final_content,
                status=AgentStatesEnum.COMPLETED,
            )
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


class ResearchSGRToolCallingAgent(SGRToolCallingAgent):
    """Agent for deep research tasks."""

    def __init__(
        self,
        task: str,
        openai_client: AsyncOpenAI,
        agent_config: AgentConfig,
        toolkit: list[Type[BaseTool]],
        def_name: str | None = None,
        **kwargs: dict,
    ):
        research_toolkit = [WebSearchTool, ExtractPageContentTool, CreateReportTool, FinalAnswerTool]
        super().__init__(
            task=task,
            openai_client=openai_client,
            agent_config=agent_config,
            toolkit=research_toolkit + [t for t in toolkit if t not in research_toolkit],
            def_name=def_name,
            **kwargs,
        )

    async def _prepare_tools(self) -> list[ChatCompletionFunctionToolParam]:
        """Prepare available tools for the current agent state and progress."""
        tools = set(self.toolkit)
        if self._context.iteration >= self.config.execution.max_iterations:
            tools = {
                ReasoningTool,
                CreateReportTool,
                FinalAnswerTool,
            }
        if self._context.clarifications_used >= self.config.execution.max_clarifications:
            tools -= {
                ClarificationTool,
            }
        if self._context.searches_used >= self.config.search.max_searches:
            tools -= {
                WebSearchTool,
            }
        return [pydantic_function_tool(tool, name=tool.tool_name, description="") for tool in tools]
