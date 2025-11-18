from typing import Literal, Type

from openai import AsyncOpenAI, pydantic_function_tool
from openai.types.chat import ChatCompletionFunctionToolParam

from sgr_deep_research.core.agent_definition import ExecutionConfig, LLMConfig, PromptsConfig
from sgr_deep_research.core.agents.sgr_agent import SGRAgent
from sgr_deep_research.core.models import AgentStatesEnum
from sgr_deep_research.core.tools import (
    BaseTool,
    CreateReportTool,
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
        llm_config: LLMConfig,
        prompts_config: PromptsConfig,
        execution_config: ExecutionConfig,
        toolkit: list[Type[BaseTool]] | None = None,
    ):
        super().__init__(
            task=task,
            openai_client=openai_client,
            llm_config=llm_config,
            prompts_config=prompts_config,
            execution_config=execution_config,
            toolkit=toolkit,
        )
        self.toolkit.append(ReasoningTool)
        self.tool_choice: Literal["required"] = "required"

    async def _prepare_tools(self) -> list[ChatCompletionFunctionToolParam]:
        """Prepare available tools for current agent state and progress."""
        tools = set(self.toolkit)
        if self._context.iteration >= self.max_iterations:
            tools = {
                ReasoningTool,
                CreateReportTool,
                FinalAnswerTool,
            }
        if self._context.searches_used >= self.max_searches:
            tools -= {
                WebSearchTool,
            }
        return [pydantic_function_tool(tool, name=tool.tool_name, description="") for tool in tools]

    async def _reasoning_phase(self) -> ReasoningTool:
        # Don't stream chunks during reasoning to avoid duplicate tool calls
        completion = await self.openai_client.beta.chat.completions.parse(
            model=self.llm_config.model,
            messages=await self._prepare_context(),
            max_tokens=self.llm_config.max_tokens,
            temperature=self.llm_config.temperature,
            tools=await self._prepare_tools(),
            tool_choice={"type": "function", "function": {"name": ReasoningTool.tool_name}},
        )
        reasoning: ReasoningTool = completion.choices[0].message.tool_calls[0].function.parsed_arguments
        
        # Display reasoning in OpenWebUI format
        self._display_reasoning(reasoning)
        
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
        self.conversation.append(
            {"role": "tool", "content": tool_call_result, "tool_call_id": f"{self._context.iteration}-reasoning"}
        )
        self._log_reasoning(reasoning)
        return reasoning
    
    def _display_reasoning(self, reasoning: ReasoningTool):
        """Display reasoning phase with status message and collapsible details."""
        import html
        
        # Send status message with ellipsis for thinking process
        status_message = f"… {reasoning.current_situation}\n\n"
        self.streaming_generator.add_chunk_from_str(status_message)
        
        # Format detailed reasoning content
        reasoning_content = f"""**Plan Status:**
{reasoning.plan_status}

**Reasoning Steps:**
{chr(10).join(f'{i+1}. {step}' for i, step in enumerate(reasoning.reasoning_steps))}

**Remaining Steps:**
{chr(10).join(f'- {step}' for step in reasoning.remaining_steps)}

**Searches Used:** {self._context.searches_used}
**Clarifications Used:** {self._context.clarifications_used}
**Enough Data:** {'✅ Yes' if reasoning.enough_data else '❌ No'}
**Task Completed:** {'✅ Yes' if reasoning.task_completed else '⏳ In Progress'}"""
        
        # Create HTML details block for reasoning (collapsible)
        # Note: OpenWebUI's marked extension requires newline after <details> tag
        reasoning_html = (
            f'<details type="reasoning" done="true">\n'
            f'<summary>Просмотр детального анализа</summary>\n'
            f'{reasoning_content}\n'
            f'</details>\n\n'
        )
        
        self.streaming_generator.add_chunk_from_str(reasoning_html)

    async def _select_action_phase(self, reasoning: ReasoningTool) -> BaseTool:
        # Don't stream chunks during action selection to avoid duplicate tool calls
        completion = await self.openai_client.beta.chat.completions.parse(
            model=self.llm_config.model,
            messages=await self._prepare_context(),
            max_tokens=self.llm_config.max_tokens,
            temperature=self.llm_config.temperature,
            tools=await self._prepare_tools(),
            tool_choice=self.tool_choice,
        )

        try:
            tool = completion.choices[0].message.tool_calls[0].function.parsed_arguments
        except (IndexError, AttributeError, TypeError):
            # LLM returned a text response instead of a tool call - treat as completion
            final_content = completion.choices[0].message.content or "Task completed successfully"
            tool = FinalAnswerTool(
                reasoning="Agent decided to complete the task",
                completed_steps=[final_content],
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
        # Don't send tool call here - it will be sent with result in _action_phase
        return tool

    async def _action_phase(self, tool: BaseTool) -> str:
        tool_call_id = f"{self._context.iteration}-action"
        
        # Parse tool reasoning if available
        tool_reasoning = None
        if hasattr(tool, 'reasoning') and tool.reasoning:
            tool_reasoning = tool.reasoning
        
        # Send status message with simple arrow for tool execution
        tool_display_name = tool.tool_name.replace('tool', '').replace('_', ' ').title()
        if tool_reasoning:
            status_message = f"▹ {tool_reasoning}\n\n"
        else:
            status_message = f"▹ **Выполняю {tool_display_name}...**\n\n"
        self.streaming_generator.add_chunk_from_str(status_message)
        
        # Show tool execution start with shimmer animation
        self.streaming_generator.add_tool_call_start(
            tool_call_id,
            tool.tool_name,
            tool.model_dump_json()
        )
        
        # Execute tool
        result = await tool(self._context)
        self.conversation.append(
            {"role": "tool", "content": result, "tool_call_id": tool_call_id}
        )
        
        # Send completed result
        self.streaming_generator.add_tool_call_with_result(
            tool_call_id,
            tool.tool_name,
            tool.model_dump_json(),
            result
        )
        
        self._log_tool_execution(tool, result)
        return result
