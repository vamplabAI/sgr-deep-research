"""Agents module for SGR Deep Research."""

from sgr_deep_research.core.agents.base_agent import BaseAgent
from sgr_deep_research.core.agents.batch_generator_agent import BatchGeneratorAgent
from sgr_deep_research.core.agents.sgr_agent import SGRResearchAgent
from sgr_deep_research.core.agents.sgr_auto_tools_agent import SGRAutoToolCallingResearchAgent
from sgr_deep_research.core.agents.sgr_so_tools_agent import SGRSOToolCallingResearchAgent
from sgr_deep_research.core.agents.sgr_tools_agent import SGRToolCallingResearchAgent
from sgr_deep_research.core.agents.tools_agent import ToolCallingResearchAgent

__all__ = [
    "BaseAgent",
    "BatchGeneratorAgent",
    "SGRResearchAgent",
    "SGRToolCallingResearchAgent",
    "SGRAutoToolCallingResearchAgent",
    "ToolCallingResearchAgent",
    "SGRSOToolCallingResearchAgent",
]
