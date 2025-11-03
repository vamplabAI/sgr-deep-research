from typing import Literal, Type
from warnings import warn

from openai import AsyncOpenAI

from sgr_deep_research.core.agents.sgr_tool_calling_agent import SGRToolCallingAgent
from sgr_deep_research.core.tools import BaseTool
from sgr_deep_research.settings import LLMConfig, PromptsConfig


class SGRAutoToolCallingAgent(SGRToolCallingAgent):
    """SGR Tool Calling Research Agent variation for benchmark with automatic
    tool selection."""

    name: str = "sgr_auto_tool_calling_agent"

    def __init__(
            self,
            task: str,
            openai_client: AsyncOpenAI,
            llm_config: LLMConfig,
            prompts_config: PromptsConfig,
            toolkit: list[Type[BaseTool]] | None = None,
            max_clarifications: int = 3,
            max_searches: int = 4,
            max_iterations: int = 10,
    ):
        super().__init__(
            task, openai_client, llm_config, prompts_config, toolkit, max_clarifications, max_searches, max_iterations
        )
        self.tool_choice: Literal["auto"] = "auto"
        warn(
            "SGRAutoToolCallingAgent is deprecated and will be removed in the future. "
            "This agent shows lower efficiency and stability based on our benchmarks.",
            DeprecationWarning,
        )
