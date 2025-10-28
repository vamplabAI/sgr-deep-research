from typing import Literal, Type
from warnings import warn

from sgr_deep_research.core.agents.sgr_tools_agent import SGRToolCallingResearchAgent
from sgr_deep_research.core.tools import BaseTool
from sgr_deep_research.settings import OpenAIConfig, PromptsConfig


class SGRAutoToolCallingResearchAgent(SGRToolCallingResearchAgent):
    """SGR Tool Calling Research Agent variation for benchmark with automatic
    tool selection."""

    name: str = "sgr_auto_tool_calling_agent"

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
        self.tool_choice: Literal["auto"] = "auto"
        warn(
            "SGRAutoToolCallingResearchAgent is deprecated and will be removed in the future. "
            "This agent shows lower efficiency and stability based on our benchmarks.",
            DeprecationWarning,
        )
