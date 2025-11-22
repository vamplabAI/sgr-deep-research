from typing import Literal, Type

from openai import AsyncOpenAI, pydantic_function_tool
from openai.types.chat import ChatCompletionToolParam

from sgr_deep_research.core.agent_definition import ExecutionConfig, LLMConfig, PromptsConfig
from sgr_deep_research.core.agents.sgr_agent import SGRAgent
from sgr_deep_research.core.models import AgentStatesEnum
from sgr_deep_research.core.tools import (
    BaseTool,
    ClarificationTool,
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

    async def _prepare_tools(self) -> list[ChatCompletionToolParam]:
        """Prepare available tools for current agent state and progress."""
        tools = set(self.toolkit)
        if self._context.iteration >= self.max_iterations:
            tools = {
                ReasoningTool,
                CreateReportTool,
                FinalAnswerTool,
            }
        if self._context.clarifications_used >= self.max_clarifications:
            tools -= {
                ClarificationTool,
            }
        if self._context.searches_used >= self.max_searches:
            tools -= {
                WebSearchTool,
            }
        return [pydantic_function_tool(tool, name=tool.tool_name, description="") for tool in tools]

    async def _reasoning_phase(self) -> ReasoningTool:
        # GigaChat/Legacy function calling path
        tools_params = await self._prepare_tools()
        functions = [t["function"] for t in tools_params if "function" in t]

        reasoning = None

        messages = await self._prepare_context()

        completion = await self.openai_client.chat.completions.create(
            model=self.llm_config.model,
            messages=messages,
            max_tokens=self.llm_config.max_tokens,
            temperature=self.llm_config.temperature,
            functions=functions,
            function_call={"name": ReasoningTool.tool_name},
            stream=False
        )

        message = completion.choices[0].message

        tool_args_str = None
        if message.function_call and message.function_call.name == ReasoningTool.tool_name:
            tool_args_str = message.function_call.arguments
        elif message.tool_calls:
            # Try to find ReasoningTool in tool_calls
            for tc in message.tool_calls:
                if tc.function.name == ReasoningTool.tool_name:
                    tool_args_str = tc.function.arguments
                    break

        if tool_args_str:
            reasoning = ReasoningTool.model_validate_json(tool_args_str)
        else:
            error_msg = f"Model did not call {ReasoningTool.tool_name}. Content: {message.content}"
            raise ValueError(f"Model failed to select ReasoningTool. Error: {error_msg}")

        # Use legacy function_call format for history
        self.conversation.append(
            {
                "role": "assistant",
                "content": "",
                "function_call": {
                    "name": reasoning.tool_name,
                    "arguments": reasoning.model_dump(),
                }
            }
        )
        tool_call_result = await reasoning(self._context)
        self.conversation.append(
            {
                "role": "function",
                "name": reasoning.tool_name,
                "content": tool_call_result
            }
        )
        self._log_reasoning(reasoning)
        return reasoning

    async def _select_action_phase(self, reasoning: ReasoningTool) -> BaseTool:
        # GigaChat/Legacy path
        tools_params = await self._prepare_tools()
        functions = [t["function"] for t in tools_params if "function" in t]

        tool = None

        messages = await self._prepare_context()

        completion = await self.openai_client.chat.completions.create(
            model=self.llm_config.model,
            messages=messages,
            max_tokens=self.llm_config.max_tokens,
            temperature=self.llm_config.temperature,
            functions=functions,
            function_call="auto",
            stream=False
        )

        message = completion.choices[0].message
        tool_name = None
        tool_args_str = None

        if message.function_call:
            tool_name = message.function_call.name
            tool_args_str = message.function_call.arguments
        elif message.tool_calls:
            tool_call = message.tool_calls[0]
            tool_name = tool_call.function.name
            tool_args_str = tool_call.function.arguments
        else:
            # Fallback: check if content implies completion
            pass

        if tool_name:
            # Find tool class
            candidate_tools = set(self.toolkit)
            candidate_tools.update({ClarificationTool, CreateReportTool, FinalAnswerTool, WebSearchTool, ReasoningTool})

            tool_cls = next((t for t in candidate_tools if t.tool_name == tool_name), None)
            if tool_cls:
                tool = tool_cls.model_validate_json(tool_args_str)
            else:
                error_msg = f"Tool {tool_name} not found in toolkit"
                raise ValueError(error_msg)
        else:
            # No tool called.
            # Fallback to FinalAnswer if content exists
            if 'completion' in locals() and completion.choices[0].message.content:
                final_content = completion.choices[0].message.content
                tool = FinalAnswerTool(
                    reasoning="Agent decided to complete the task (Fallback)",
                    completed_steps=[final_content],
                    status=AgentStatesEnum.COMPLETED,
                )
            else:
                error_msg = f"No function called and no content. Content: {message.content}"
                raise ValueError(error_msg)

        if not isinstance(tool, BaseTool):
            raise ValueError("Selected tool is not a valid BaseTool instance")

        # Use legacy function_call format for history
        self.conversation.append(
            {
                "role": "assistant",
                "content": "",
                "function_call": {
                    "name": tool.tool_name,
                    "arguments": tool.model_dump(),
                }
            }
        )
        self.streaming_generator.add_tool_call(
            f"{self._context.iteration}-action", tool.tool_name, tool.model_dump_json()
        )
        return tool
