from typing import Literal, Type
import time
import logging

from openai import AsyncOpenAI, pydantic_function_tool
from openai.types.chat import ChatCompletionFunctionToolParam

from sgr_agent_core.agent_config import AgentConfig
from sgr_agent_core.agents.sgr_agent import SGRAgent
from sgr_agent_core.models import AgentStatesEnum
from sgr_agent_core.tools import (
    BaseTool,
    CreateReportTool,
    FinalAnswerTool,
    ReasoningTool,
    WebSearchTool,
)

logger = logging.getLogger(__name__)


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
        self.toolkit.append(ReasoningTool)
        self.tool_choice: Literal["required"] = "required"
    
    async def execute(self):
        """Execute agent with new architecture - no separate reasoning phase."""
        import traceback
        
        total_start_time = time.time()
        self.logger.info(f"🚀 Starting for task: '{self.task}'")
        try:
            while self._context.state not in AgentStatesEnum.FINISH_STATES.value:
                self._context.iteration += 1
                step_start_time = time.time()
                self.logger.info(f"Step {self._context.iteration} started")

                # Let LLM decide which tool to use (including optional ReasoningTool)
                action_tool = await self._select_action_phase()
                await self._action_phase(action_tool)
                
                step_elapsed = time.time() - step_start_time
                self.logger.info(f"⏱️  [TIMING] Step {self._context.iteration} completed in {step_elapsed:.2f}s")

        except Exception as e:
            self.logger.error(f"❌ Agent execution error: {str(e)}")
            self._context.state = AgentStatesEnum.FAILED
            traceback.print_exc()
        finally:
            total_elapsed = time.time() - total_start_time
            self.logger.info(f"⏱️  [TIMING] ✅ Total execution time: {total_elapsed:.2f}s ({self._context.iteration} steps)")
            self.logger.info(f"⏱️  [TIMING] 📊 Average per step: {total_elapsed/max(self._context.iteration, 1):.2f}s")
            
            if self.streaming_generator is not None:
                # Don't pass content here - it's already streamed by FinalAnswerTool
                self.streaming_generator.finish()
            self._save_agent_log()

    async def _prepare_tools(self) -> list[ChatCompletionFunctionToolParam]:
        """Prepare available tools for current agent state and progress."""
        tools = set(self.toolkit)
        
        # Check if last reasoning indicated task completion
        if hasattr(self._context, 'current_step_reasoning') and self._context.current_step_reasoning:
            reasoning = self._context.current_step_reasoning
            # If task is completed or enough data collected, only allow FinalAnswerTool
            if (hasattr(reasoning, 'task_completed') and reasoning.task_completed) or \
               (hasattr(reasoning, 'enough_data') and reasoning.enough_data):
                logger.info("🎯 Task marked as complete - restricting to FinalAnswerTool only")
                tools = {FinalAnswerTool}
                return [pydantic_function_tool(tool, name=tool.tool_name, description="") for tool in tools]
        
        if self._context.iteration >= self.config.execution.max_iterations:
            tools = {
                ReasoningTool,
                CreateReportTool,
                FinalAnswerTool,
            }
        if hasattr(self.config, 'search') and self._context.searches_used >= self.config.search.max_searches:
            tools -= {
                WebSearchTool,
            }
        return [pydantic_function_tool(tool, name=tool.tool_name, description="") for tool in tools]

    async def _generate_final_answer_streaming(self) -> None:
        """Generate final answer using LLM streaming after FinalAnswerTool signals readiness.
        
        Делаем отдельный completion call без tools для генерации финального ответа,
        используя весь контекст разговора с результатами поиска.
        """
        start_time = time.time()
        logger.info("⏱️  [TIMING] Final answer generation started")
        
        # Формируем промпт для финального ответа, чтобы направить LLM на правильный формат
        # Промпт зависит от типа агента (определяем по toolkit)
        toolkit_names = [tool.tool_name if hasattr(tool, 'tool_name') else tool.__name__ for tool in self.toolkit]
        
        # Проверяем, является ли это агентом для работы с товарами (Vkusvill, Grocery)
        is_shopping_agent = any(
            'vkusvill' in name.lower() or 'grocery' in name.lower() or 'shop' in name.lower()
            for name in toolkit_names
        )
        
        if is_shopping_agent:
            # Промпт для агентов работы с товарами
            final_answer_prompt = (
                "Теперь предоставь финальный ответ на основе собранной информации.\n\n"
                "ВАЖНО:\n"
                "- Включи ВСЕ найденные товары с изображениями\n"
                "- Используй формат: ![Название](URL) на отдельной строке после названия\n"
                "- Добавь цену, вес/объем, рейтинг для каждого товара\n"
                "- Предложи несколько вариантов для выбора\n"
                "- Добавь ссылки на товары\n"
                "- Отвечай ТОЛЬКО на русском языке"
            )
        else:
            # Универсальный промпт для других агентов (Confluence, Beeline, и т.д.)
            final_answer_prompt = (
                "Теперь предоставь финальный ответ на основе собранной информации.\n\n"
                "ВАЖНО:\n"
                "- Используй информацию из всех найденных источников\n"
                "- Структурируй ответ логично и понятно\n"
                "- Добавь ссылки на источники информации\n"
                "- Если нужно сравнение - используй таблицы\n"
                "- Отвечай на языке пользовательского запроса"
            )
        
        messages = self.conversation + [
            {
                "role": "user",
                "content": final_answer_prompt
            }
        ]
        
        try:
            # Make streaming completion call WITHOUT tools
            stream = await self.openai_client.chat.completions.create(
                model=self.config.llm.model,
                messages=messages,
                max_tokens=self.config.llm.max_tokens,
                temperature=self.config.llm.temperature,
                stream=True,  # Enable streaming
                extra_body={"litellm_session_id": self.id},
            )
            
            # Stream the response in real-time
            full_response = ""
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    self.streaming_generator.add_chunk_from_str(content)
            
            # Save to context
            self._context.execution_result = full_response
            
            # Add assistant response to conversation
            self.conversation.append({
                "role": "assistant",
                "content": full_response
            })
            
            elapsed = time.time() - start_time
            logger.info(f"⏱️  [TIMING] Final answer generated in {elapsed:.2f}s ({len(full_response)} chars)")
            
        except Exception as e:
            logger.error(f"❌ Error generating final answer: {e}")
            error_message = "Извините, произошла ошибка при формировании финального ответа."
            self.streaming_generator.add_chunk_from_str(error_message)
            self._context.execution_result = error_message
    
    async def _select_action_phase(self) -> BaseTool | list[BaseTool] | str:
        """Select action(s) to execute - LLM decides which tools to use (auto mode)."""
        start_time = time.time()
        logger.info("⏱️  [TIMING] Action selection phase started")
        
        # Let LLM decide which tools to call (including optional ReasoningTool)
        completion = await self.openai_client.beta.chat.completions.parse(
            model=self.config.llm.model,
            messages=await self._prepare_context(),
            max_tokens=self.config.llm.max_tokens,
            temperature=self.config.llm.temperature,
            tools=await self._prepare_tools(),
            tool_choice="auto",  # LLM decides when to use tools
            parallel_tool_calls=True,  # Enable parallel tool calls
            extra_body={"litellm_session_id": self.id},
        )

        try:
            tool_calls = completion.choices[0].message.tool_calls
            if not tool_calls:
                raise IndexError("No tool calls found - LLM returned text response")
            
            # Parse all tool calls
            tools = []
            formatted_tool_calls = []
            
            for idx, tc in enumerate(tool_calls):
                tool = tc.function.parsed_arguments
                if not isinstance(tool, BaseTool):
                    raise ValueError(f"Tool call {idx} is not a valid BaseTool instance")
                tools.append(tool)
                formatted_tool_calls.append({
                    "type": "function",
                    "id": f"{self._context.iteration}-action-{idx}",
                    "function": {
                        "name": tool.tool_name,
                        "arguments": tool.model_dump_json(),
                    },
                })
            
            # Add all tool calls to conversation
            self.conversation.append({
                "role": "assistant",
                "content": "",
                "tool_calls": formatted_tool_calls,
            })
            
            # Return single tool or list of tools for parallel execution
            elapsed = time.time() - start_time
            logger.info(f"⏱️  [TIMING] Action selection completed in {elapsed:.2f}s ({len(tools)} tools selected)")
            return tools[0] if len(tools) == 1 else tools
            
        except (IndexError, AttributeError, TypeError):
            # LLM returned text response - stream it as final answer
            logger.info("⚡ [OPTIMIZATION] LLM returned direct text response, streaming as final answer")
            
            final_content = completion.choices[0].message.content or "Task completed successfully"
            
            # Stream the content (simulate streaming for already-received content)
            chunk_size = 50
            for i in range(0, len(final_content), chunk_size):
                chunk = final_content[i:i + chunk_size]
                self.streaming_generator.add_chunk_from_str(chunk)
            
            # Save to context and mark as completed
            self._context.execution_result = final_content
            self._context.state = AgentStatesEnum.COMPLETED
            
            self.conversation.append({
                "role": "assistant",
                "content": final_content,
            })
            
            elapsed = time.time() - start_time
            logger.info(f"⏱️  [TIMING] Direct text response streamed in {elapsed:.2f}s")
            return "FINAL_ANSWER_STREAMED"

    async def _action_phase(self, tool_or_tools: BaseTool | list[BaseTool] | str) -> str:
        """Execute tool(s) - supports parallel execution for multiple tools with timing."""
        import asyncio
        phase_start_time = time.time()
        
        # Handle special flag for direct final answer streaming
        if tool_or_tools == "FINAL_ANSWER_STREAMED":
            logger.info("⏱️  [TIMING] Action phase skipped (final answer already streamed)")
            return "Final answer streamed directly"
        
        # Handle both single tool and multiple tools
        tools = [tool_or_tools] if isinstance(tool_or_tools, BaseTool) else tool_or_tools
        
        logger.info(f"⏱️  [TIMING] Action phase started ({len(tools)} tools)")
        
        # If multiple tools, execute in parallel
        if len(tools) > 1:
            self.streaming_generator.add_chunk_from_str(f"⚡ **Параллельное выполнение {len(tools)} инструментов...**\n\n")
        
        async def execute_single_tool(tool: BaseTool, idx: int) -> tuple[str, str, str]:
            """Execute single tool and return result with metadata and timing."""
            tool_call_id = f"{self._context.iteration}-action-{idx}"
            tool_start_time = time.time()
            
            # Парсим reasoning из инструмента, чтобы показать пользователю логику агента
            tool_reasoning = None
            if hasattr(tool, 'reasoning') and tool.reasoning:
                tool_reasoning = tool.reasoning
            
            # Отправляем reasoning как простой текст, чтобы обеспечить читаемость
            # ВАЖНО: Не используем details блок и специальные символы (▹), 
            # так как OpenWebUI может интерпретировать их как специальный формат
            tool_display_name = tool.tool_name.replace('tool', '').replace('_', ' ').title()
            if tool_reasoning:
                # Используем emoji 💭 вместо ▹, чтобы избежать автоматического оборачивания в <summary>
                status_message = f"💭 {tool_reasoning}\n\n"
            else:
                status_message = f"⚙️ **Выполняю {tool_display_name}...**\n\n"
            self.streaming_generator.add_chunk_from_str(status_message)
            
            # Show tool execution start with shimmer animation
            self.streaming_generator.add_tool_call_start(
                tool_call_id,
                tool.tool_name,
                tool.model_dump_json()
            )
            
            # Execute tool
            result = await tool(self._context, self.config)
            tool_elapsed = time.time() - tool_start_time
            logger.info(f"⏱️  [TIMING] Tool '{tool.tool_name}' executed in {tool_elapsed:.2f}s")
            
            # Отправляем завершённый результат с деталями, чтобы обеспечить отладку
            self.streaming_generator.add_tool_call_with_result(
                tool_call_id,
                tool.tool_name,
                tool.model_dump_json(),
                result
            )
            
            self._log_tool_execution(tool, result)
            return tool_call_id, result, tool.tool_name
        
        # Execute all tools in parallel
        results = await asyncio.gather(
            *[execute_single_tool(tool, idx) for idx, tool in enumerate(tools)]
        )
        
        # Add all results to conversation
        for idx, (tool_call_id, result, tool_name) in enumerate(results):
            self.conversation.append(
                {"role": "tool", "content": result, "tool_call_id": tool_call_id}
            )
            
            # Save ReasoningTool to context for next iteration's tool selection
            if tool_name == "reasoningtool":
                tool = tools[idx]
                self._context.current_step_reasoning = tool
                logger.info(f"💭 Saved reasoning to context: task_completed={getattr(tool, 'task_completed', False)}, enough_data={getattr(tool, 'enough_data', False)}")
            
            # Check if FinalAnswerTool was executed - trigger final answer generation
            if tool_name == "finalanswertool":
                logger.info("🎯 FinalAnswerTool detected - generating final answer with LLM streaming")
                await self._generate_final_answer_streaming()
        
        # Combine results for single return value
        phase_elapsed = time.time() - phase_start_time
        logger.info(f"⏱️  [TIMING] Action phase completed in {phase_elapsed:.2f}s ({len(tools)} tools)")
        
        if len(results) == 1:
            return results[0][1]
        else:
            combined_result = "\n\n".join([
                f"**{tool_name}:**\n{result}" 
                for _, result, tool_name in results
            ])
            return combined_result


class ResearchSGRToolCallingAgent(SGRToolCallingAgent):
    """Agent for deep research tasks with extended toolkit."""

    def __init__(
        self,
        task: str,
        openai_client: AsyncOpenAI,
        agent_config: AgentConfig,
        toolkit: list[Type[BaseTool]],
        def_name: str | None = None,
        **kwargs: dict,
    ):
        from sgr_agent_core.tools import ExtractPageContentTool
        
        research_toolkit = [WebSearchTool, ExtractPageContentTool, CreateReportTool, FinalAnswerTool]
        super().__init__(
            task=task,
            openai_client=openai_client,
            agent_config=agent_config,
            toolkit=research_toolkit + [t for t in toolkit if t not in research_toolkit],
            def_name=def_name,
            **kwargs,
        )
