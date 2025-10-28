from typing import Type
from warnings import warn

from sgr_deep_research.core import BaseTool
from sgr_deep_research.core.agents.sgr_tools_agent import SGRToolCallingResearchAgent
from sgr_deep_research.core.tools import ReasoningTool
from sgr_deep_research.settings import OpenAIConfig, PromptsConfig


class SGRSOToolCallingResearchAgent(SGRToolCallingResearchAgent):
    """Agent that uses OpenAI native function calling to select and execute
    tools based on SGR like reasoning scheme."""

    name: str = "sgr_so_tool_calling_agent"

    def __init__(
        self,
        task: str,
        openai_config: OpenAIConfig,
        prompts_config: PromptsConfig,
        toolkit: list[Type[BaseTool]] | None = None,
        max_clarifications: int = 3,
        max_searches: int = 4,
        max_iterations: int = 10,
    ):
        super().__init__(task, openai_config, prompts_config, toolkit, max_clarifications, max_searches, max_iterations)
        warn(
            "SGRSOToolCallingResearchAgent is deprecated and will be removed in the future. "
            "This agent shows lower efficiency and stability based on our benchmarks.",
            DeprecationWarning,
        )

    async def _reasoning_phase(self) -> ReasoningTool:
        async with self.openai_client.chat.completions.stream(
            model=self.openai_config.model,
            messages=await self._prepare_context(),
            max_tokens=self.openai_config.max_tokens,
            temperature=self.openai_config.temperature,
            tools=await self._prepare_tools(),
            tool_choice={"type": "function", "function": {"name": ReasoningTool.tool_name}},
        ) as stream:
            async for event in stream:
                if event.type == "chunk":
                    self.streaming_generator.add_chunk(event.chunk)
            reasoning: ReasoningTool = (  # noqa
                (await stream.get_final_completion()).choices[0].message.tool_calls[0].function.parsed_arguments  #
            )
        async with self.openai_client.chat.completions.stream(
            model=self.openai_config.model,
            response_format=ReasoningTool,
            messages=await self._prepare_context(),
            max_tokens=self.openai_config.max_tokens,
            temperature=self.openai_config.temperature,
        ) as stream:
            async for event in stream:
                if event.type == "chunk":
                    self.streaming_generator.add_chunk(event)
        reasoning: ReasoningTool = (await stream.get_final_completion()).choices[0].message.parsed
        tool_call_result = await reasoning(self._context)
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
                            "arguments": "{}",
                        },
                    }
                ],
            }
        )
        self.conversation.append(
            {"role": "tool", "content": tool_call_result, "tool_call_id": f"{self._context.iteration}-reasoning"}
        )
        self._log_reasoning(reasoning)
        return reasoning
