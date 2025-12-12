from typing import Literal, Type

from openai import AsyncOpenAI, pydantic_function_tool
from openai.types.chat import ChatCompletionToolParam

from sgr_deep_research.core.agent_definition import ExecutionConfig, LLMConfig, PromptsConfig
from sgr_deep_research.gigachat_compatability.base_agent import BaseAgent_functional
from sgr_deep_research.gigachat_compatability.base_tool import BaseTool_functional
from sgr_deep_research.gigachat_compatability.tools.clarification_tool import ClarificationTool_functional
from sgr_deep_research.gigachat_compatability.tools.create_report_tool import CreateReportTool_functional
from sgr_deep_research.gigachat_compatability.tools.final_answer_tool import FinalAnswerTool_functional
from sgr_deep_research.gigachat_compatability.tools.web_search_tool import WebSearchTool_functional


class ToolCallingAgent_functional(BaseAgent_functional):
    """Tool Calling Research Agent relying entirely on LLM native function
    calling."""

    name: str = "tool_calling_agent"

    def __init__(
        self,
        task: str,
        openai_client: AsyncOpenAI,
        llm_config: LLMConfig,
        prompts_config: PromptsConfig,
        execution_config: ExecutionConfig,
        toolkit: list[Type[BaseTool_functional]] | None = None
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
        self.tool_choice: Literal["required"] = "required"

    async def _prepare_tools(self) -> list[ChatCompletionToolParam]:
        """Prepare tool classes with current context limits."""
        tools = set(self.toolkit)
        if self._context.iteration >= self.max_iterations:
            tools = {
                CreateReportTool_functional,
                FinalAnswerTool_functional,
            }
        if self._context.clarifications_used >= self.max_clarifications:
            tools -= {
                ClarificationTool_functional,
            }
        if self._context.searches_used >= self.max_searches:
            tools -= {
                WebSearchTool_functional,
            }
        return [pydantic_function_tool(tool, name=tool.tool_name, description="") for tool in tools]

    async def _reasoning_phase(self) -> None:
        """No explicit reasoning phase, reasoning is done internally by LLM."""
        return None

    async def _select_action_phase(self, reasoning=None) -> BaseTool_functional:
        # GigaChat specific: Use legacy 'functions' parameter instead of 'tools'
        # This often works better for models with older OpenAI API compatibility
        tools_params = await self._prepare_tools()
        
        # Extract 'function' definitions from the tools parameters
        functions = []
        for t in tools_params:
            # t is a ChatCompletionToolParam (dict) with keys 'type' and 'function'
            if "function" in t:
                functions.append(t["function"])
        
        messages = await self._prepare_context()

        completion = await self.openai_client.chat.completions.create(
            model=self.llm_config.model,
            messages=messages,
            max_tokens=self.llm_config.max_tokens,
            temperature=self.llm_config.temperature,
            functions=functions,
            function_call="auto", # Use 'auto' for function calling
            stream=False
        )

        self._accumulate_tokens(completion.usage)
        
        message = completion.choices[0].message
        
        # Check for legacy function_call response
        tool_name = None
        tool_args_str = None

        if message.function_call:
                tool_name = message.function_call.name
                tool_args_str = message.function_call.arguments
        # Fallback check for tool_calls (just in case)
        elif message.tool_calls:
            tool_call = message.tool_calls[0]
            tool_name = tool_call.function.name
            tool_args_str = tool_call.function.arguments
        else:
            error_msg = f"Model returned no function call. Content: {message.content}"
            raise ValueError(f"Model failed to select a tool. Error: {error_msg}")

        # Find the tool class
        candidate_tools = set(self.toolkit)
        candidate_tools.update({ClarificationTool_functional, CreateReportTool_functional, FinalAnswerTool_functional, WebSearchTool_functional})
        
        tool_cls = next((t for t in candidate_tools if t.tool_name == tool_name), None)
        
        if not tool_cls:
            raise ValueError(f"Tool {tool_name} not found in toolkit")
        # print(f"{tool_args_str=}")

        tool = tool_cls.model_validate(tool_args_str)

        if not isinstance(tool, BaseTool_functional):
            raise ValueError("Selected tool is not a valid BaseTool_functional instance")
            
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

    async def _action_phase(self, tool: BaseTool_functional) -> str:
        result = await tool(self._context)
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