from typing import Literal, Type

from openai import pydantic_function_tool
from openai.types.chat import ChatCompletionFunctionToolParam

from sgr_deep_research.core.agents.sgr_agent import SGRResearchAgent
from sgr_deep_research.core.models import AgentStatesEnum
from sgr_deep_research.core.tools import (
    BaseTool,
    ClarificationTool,
    FinalAnswerTool,
    ReasoningTool,
    file_system_tools,
    system_agent_tools,
)
from sgr_deep_research.settings import get_config

config = get_config()


class SGRFileAgent(SGRResearchAgent):
    """File-first agent that uses OpenAI native function calling to work with filesystem.
    Two-phase agent: reasoning phase + action phase.
    
    Focus: File search and analysis (read-only operations)
    
    Available file system tools (6 essential tools):
    - GetCurrentDirectoryTool: Get current working directory and context
    - GetSystemPathsTool: Get standard system paths (home, documents, downloads, desktop, etc.)
    - ReadFileTool: Read file contents with optional line range
    - ListDirectoryTool: List directory contents with recursive option
    - SearchInFilesTool: Search text/code within files (grep-like functionality)
    - FindFilesFastTool: Universal file search using native find command (supports patterns, size, date filters)
    
    All tools use native OS commands for optimal performance.
    Automatic filtering excludes cache dirs, node_modules, .git, etc.
    
    Usage:
        agent = SGRFileAgent(
            task="Find all PDF files in my Downloads folder from last week",
            max_iterations=10,
            working_directory="."
        )
        async for event in agent.run():
            # Process events
    """

    name: str = "sgr_file_agent"

    def __init__(
        self,
        task: str,
        toolkit: list[Type[BaseTool]] | None = None,
        max_clarifications: int = 3,
        max_iterations: int = 10,
        working_directory: str = ".",
    ):
        super().__init__(
            task=task,
            toolkit=toolkit,
            max_clarifications=max_clarifications,
            max_iterations=max_iterations,
            max_searches=0,
        )
        self.working_directory = working_directory
        self.toolkit = [
            *system_agent_tools,
            *file_system_tools,
            *(toolkit if toolkit else []),
        ]
        self.tool_choice: Literal["required"] = "required"

    async def _prepare_tools(self) -> list[ChatCompletionFunctionToolParam]:
        """Prepare available tools for current agent state and progress."""
        tools = set(self.toolkit)
        if self._context.iteration >= self.max_iterations:
            tools = {
                ReasoningTool,
                FinalAnswerTool,
            }
        if self._context.clarifications_used >= self.max_clarifications:
            tools -= {
                ClarificationTool,
            }
        return [pydantic_function_tool(tool, name=tool.tool_name, description="") for tool in tools]

    async def _reasoning_phase(self) -> ReasoningTool:
        async with self.openai_client.chat.completions.stream(
            model=config.openai.model,
            messages=await self._prepare_context(),
            max_tokens=config.openai.max_tokens,
            temperature=config.openai.temperature,
            tools=await self._prepare_tools(),
            tool_choice={"type": "function", "function": {"name": ReasoningTool.tool_name}},
        ) as stream:
            async for event in stream:
                if event.type == "chunk":
                    self.streaming_generator.add_chunk(event.chunk)
            reasoning: ReasoningTool = (
                (await stream.get_final_completion()).choices[0].message.tool_calls[0].function.parsed_arguments
            )
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

    async def _select_action_phase(self, reasoning: ReasoningTool) -> BaseTool:
        async with self.openai_client.chat.completions.stream(
            model=config.openai.model,
            messages=await self._prepare_context(),
            max_tokens=config.openai.max_tokens,
            temperature=config.openai.temperature,
            tools=await self._prepare_tools(),
            tool_choice=self.tool_choice,
        ) as stream:
            async for event in stream:
                if event.type == "chunk":
                    self.streaming_generator.add_chunk(event.chunk)

        completion = await stream.get_final_completion()

        try:
            tool = completion.choices[0].message.tool_calls[0].function.parsed_arguments
        except (IndexError, AttributeError, TypeError):
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
        self.streaming_generator.add_tool_call(
            f"{self._context.iteration}-action", tool.tool_name, tool.model_dump_json()
        )
        return tool

