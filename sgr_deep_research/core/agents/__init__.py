"""Agents module for SGR Deep Research."""

from typing import Dict, Type

from sgr_deep_research.core.agents.base_agent import BaseAgent
from sgr_deep_research.core.agents.batch_generator_agent import BatchGeneratorAgent
from sgr_deep_research.core.agents.sgr_tools_agent import SGRToolCallingResearchAgent

# Main agents dictionary - using only SGR tools agent
AGENTS: Dict[str, Type[BaseAgent]] = {
    "sgr-tools": SGRToolCallingResearchAgent,
}

# Default agent type
DEFAULT_AGENT = "sgr-tools"

__all__ = [
    "BaseAgent",
    "BatchGeneratorAgent",
    "SGRToolCallingResearchAgent",
    "AGENTS",
    "DEFAULT_AGENT",
]
