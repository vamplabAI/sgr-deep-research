from typing import Literal, Type

from openai import AsyncOpenAI, pydantic_function_tool
from openai.types.chat import ChatCompletionFunctionToolParam

from sgr_agent_core.agent_config import AgentConfig
from sgr_agent_core.base_agent import BaseAgent
from sgr_agent_core.tools import (
    BaseTool,
    ClarificationTool,
    CreateReportTool,
    ExtractPageContentTool,
    FinalAnswerTool,
    WebSearchTool,
)


class ToolCallingAgent(BaseAgent):
    """Tool Calling Research Agent relying entirely on LLM native function
    calling."""

    name: str = "tool_calling_agent"

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

    async def _reasoning_phase(self) -> None:
        """No explicit reasoning phase, reasoning is done internally by LLM."""
        return None

    async def _select_action_phase(self, reasoning=None) -> BaseTool:
        async with self.openai_client.chat.completions.stream(
            model=self.config.llm.model,
            messages=await self._prepare_context(),
            max_tokens=self.config.llm.max_tokens,
            temperature=self.config.llm.temperature,
            tools=await self._prepare_tools(),
            tool_choice=self.tool_choice,
        ) as stream:
            async for event in stream:
                if event.type == "chunk":
                    self.streaming_generator.add_chunk(event.chunk)
        tool = (await stream.get_final_completion()).choices[0].message.tool_calls[0].function.parsed_arguments

        if not isinstance(tool, BaseTool):
            raise ValueError("Selected tool is not a valid BaseTool instance")
        self.conversation.append(
            {
                "role": "assistant",
                "content": None,
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

    async def _action_phase(self, tool: BaseTool) -> str:
        result = await tool(self._context, self.config)
        self.conversation.append(
            {"role": "tool", "content": result, "tool_call_id": f"{self._context.iteration}-action"}
        )
        self.streaming_generator.add_chunk_from_str(f"{result}\n")
        self._log_tool_execution(tool, result)
        return result


class ResearchToolCallingAgent(ToolCallingAgent):
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
