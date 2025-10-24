"""Agents module for SGR Deep Research."""

from sgr_deep_research.core.agents.base_agent import BaseAgent
from sgr_deep_research.core.agents.sgr_agent import SGRResearchAgent
from sgr_deep_research.core.agents.sgr_auto_tools_agent import SGRAutoToolCallingResearchAgent
from sgr_deep_research.core.agents.sgr_infinite_auto_tool_calling_agent import SGRInfiniteAutoToolCallingAgent
from sgr_deep_research.core.agents.sgr_so_tools_agent import SGRSOToolCallingResearchAgent
from sgr_deep_research.core.agents.sgr_tools_agent import SGRToolCallingResearchAgent
from sgr_deep_research.core.agents.tools_agent import ToolCallingResearchAgent

__all__ = [
    "BaseAgent",
    "SGRResearchAgent",
    "SGRToolCallingResearchAgent",
    "SGRAutoToolCallingResearchAgent",
    "SGRInfiniteAutoToolCallingAgent",
    "ToolCallingResearchAgent",
    "SGRSOToolCallingResearchAgent",
]
