from typing import Type

from openai import AsyncOpenAI, pydantic_function_tool

from sgr_deep_research.core.agent_definition import ExecutionConfig, LLMConfig, PromptsConfig
from sgr_deep_research.core.base_agent import BaseAgent
from sgr_deep_research.core.tools import (
    BaseTool,
    ClarificationTool,
    CreateReportTool,
    FinalAnswerTool,
    NextStepToolsBuilder,
    NextStepToolStub,
    WebSearchTool,
)


class SGRAgent(BaseAgent):
    """Agent for deep research tasks using SGR framework."""

    name: str = "sgr_agent"

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
        self.max_searches = execution_config.max_searches

    async def _prepare_tools(self) -> Type[NextStepToolStub]:
        """Prepare tool classes with current context limits."""
        tools = set(self.toolkit)
        if self._context.iteration >= self.max_iterations:
            tools = {
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
        return NextStepToolsBuilder.build_NextStepTools(list(tools))

    async def _reasoning_phase(self) -> NextStepToolStub:
        # GigaChat/Legacy path using functions to simulate Structured Outputs
        next_step_cls = await self._prepare_tools()
        # Create a function definition from the model
        tool_def = pydantic_function_tool(next_step_cls, name="plan_next_step", description="Plan the next step and select a tool")
        functions = [tool_def["function"]]
        
        reasoning = None
        
        messages = await self._prepare_context()
            
        completion = await self.openai_client.chat.completions.create(
            model=self.llm_config.model,
            messages=messages,
            max_tokens=self.llm_config.max_tokens,
            temperature=self.llm_config.temperature,
            functions=functions,
            function_call={"name": "plan_next_step"},
            stream=False
        )
        
        message = completion.choices[0].message
        tool_args_str = None
        
        if message.function_call and message.function_call.name == "plan_next_step":
            tool_args_str = message.function_call.arguments
        elif message.tool_calls:
                for tc in message.tool_calls:
                    if tc.function.name == "plan_next_step":
                        tool_args_str = tc.function.arguments
                        break
                        
        if tool_args_str:
            reasoning = next_step_cls.model_validate_json(tool_args_str)
        else:
            error_msg = f"Model did not call plan_next_step. Content: {message.content}"
            raise ValueError(f"Model failed to generate structured output. Error: {error_msg}")

        # We do NOT append reasoning to conversation for SGRAgent as it is an internal thought process 
        # that resolves to a tool call in the next step, or it might be appended if desired.
        # The original SGRAgent didn't seem to append it.
        self._log_reasoning(reasoning)
        return reasoning

    async def _select_action_phase(self, reasoning: NextStepToolStub) -> BaseTool:
        tool = reasoning.function
        if not isinstance(tool, BaseTool):
            raise ValueError("Selected tool is not a valid BaseTool instance")
        
        # Use legacy function_call format for history
        self.conversation.append(
            {
                "role": "assistant",
                "content": reasoning.remaining_steps[0] if reasoning.remaining_steps else "Completing",
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

    async def _action_phase(self, tool: BaseTool) -> str:
        result = await tool(self._context)
        # Use legacy function role for history
        self.conversation.append(
            {
                "role": "function",
                "name": tool.tool_name,
                "content": result
            }
        )
        self.streaming_generator.add_chunk_from_str(f"{result}\n")
        self._log_tool_execution(tool, result)
        return result
