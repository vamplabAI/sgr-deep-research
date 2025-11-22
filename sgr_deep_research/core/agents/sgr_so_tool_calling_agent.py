from typing import Type
from warnings import warn

from openai import AsyncOpenAI, pydantic_function_tool

from sgr_deep_research.core.agent_definition import ExecutionConfig, LLMConfig, PromptsConfig
from .sgr_tool_calling_agent import SGRToolCallingAgent
from sgr_deep_research.core.tools import BaseTool, ReasoningTool


class SGRSOToolCallingAgent(SGRToolCallingAgent):
    """Agent that uses OpenAI native function calling to select and execute
    tools based on SGR like reasoning scheme."""

    name: str = "sgr_so_tool_calling_agent"

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
        warn(
            "SGRSOToolCallingAgent is deprecated and will be removed in the future. "
            "This agent shows lower efficiency and stability based on our benchmarks.",
            DeprecationWarning,
        )

    async def _reasoning_phase(self) -> ReasoningTool:
        # GigaChat/Legacy implementation
        # Since GigaChat doesn't support response_format with Pydantic models,
        # we simulate Structured Output by forcing a function call to ReasoningTool.

        # Create function definition for ReasoningTool
        tool_def = pydantic_function_tool(ReasoningTool, name=ReasoningTool.tool_name, description=ReasoningTool.description)
        functions = [tool_def["function"]]

        reasoning = None

        messages = await self._prepare_context()

        completion = await self.openai_client.chat.completions.create(
            model=self.llm_config.model,
            messages=messages,
            max_tokens=self.llm_config.max_tokens,
            temperature=self.llm_config.temperature,
            functions=functions,
            function_call={"name": ReasoningTool.tool_name}, # Force specific function
            stream=False
        )
        
        message = completion.choices[0].message
        tool_args_str = None

        if message.function_call and message.function_call.name == ReasoningTool.tool_name:
            tool_args_str = message.function_call.arguments
        elif message.tool_calls:
                for tc in message.tool_calls:
                    if tc.function.name == ReasoningTool.tool_name:
                        tool_args_str = tc.function.arguments
                        break
        
        if tool_args_str:
            reasoning = ReasoningTool.model_validate_json(tool_args_str)
        else:
            error_msg = f"Model did not call {ReasoningTool.tool_name}. Content: {message.content}"
            raise ValueError(f"Model failed to select ReasoningTool. Error: {error_msg}")

        tool_call_result = await reasoning(self._context)
        
        # Use legacy function_call format for history
        self.conversation.append(
            {
                "role": "assistant",
                "content": "",
                "function_call": {
                    "name": reasoning.tool_name,
                    "arguments": {}, # Match original which passed empty dict
                }
            }
        )
        self.conversation.append(
            {
                "role": "function",
                "name": reasoning.tool_name,
                "content": tool_call_result
            }
        )
        self._log_reasoning(reasoning)
        return reasoning
