from typing import Literal, Type

from sgr_deep_research.core.agents.sgr_tools_agent import SGRToolCallingResearchAgent
from sgr_deep_research.core.tools import BaseTool


class SGRAutoToolCallingResearchAgent(SGRToolCallingResearchAgent):
    """SGR Tool Calling Research Agent variation for benchmark with automatic
    tool selection."""

    name: str = "sgr_auto_tool_calling_agent"

    def __init__(
        self,
        task: str,
        toolkit: list[Type[BaseTool]] | None = None,
        max_clarifications: int = 3,
        max_searches: int = 4,
        max_iterations: int = 10,
    ):
        super().__init__(task, toolkit, max_clarifications, max_searches, max_iterations)
        self.tool_choice: Literal["auto"] = "auto"
