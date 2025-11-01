"""Agents module for SGR Deep Research."""

from sgr_deep_research.core.agents.base_agent import BaseAgent
from sgr_deep_research.core.agents.sgr_agent import SGRAgent
from sgr_deep_research.core.agents.sgr_auto_tool_calling_agent import SGRAutoToolCallingAgent
from sgr_deep_research.core.agents.sgr_so_tool_calling_agent import SGRSOToolCallingAgent
from sgr_deep_research.core.agents.sgr_tool_calling_agent import SGRToolCallingAgent
from sgr_deep_research.core.agents.tool_calling_agent import ToolCallingAgent

__all__ = [
    "BaseAgent",
    "SGRAgent",
    "SGRAutoToolCallingAgent",
    "SGRSOToolCallingAgent",
    "SGRToolCallingAgent",
    "ToolCallingAgent",
]
