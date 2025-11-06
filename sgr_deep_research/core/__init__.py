"""Core modules for SGR Agent Core."""

from sgr_deep_research.core.agent_definition import AgentDefinition
from sgr_deep_research.core.agent_factory import AgentFactory
from sgr_deep_research.core.agents import (  # noqa: F403
    SGRAgent,
    SGRAutoToolCallingAgent,
    SGRSOToolCallingAgent,
    SGRToolCallingAgent,
    ToolCallingAgent,
)
from sgr_deep_research.core.base_agent import BaseAgent
from sgr_deep_research.core.base_tool import BaseTool, MCPBaseTool
from sgr_deep_research.core.models import AgentStatesEnum, ResearchContext, SearchResult, SourceData
from sgr_deep_research.core.services import AgentRegistry, MCP2ToolConverter, PromptLoader, ToolRegistry
from sgr_deep_research.core.stream import OpenAIStreamingGenerator
from sgr_deep_research.core.tools import *  # noqa: F403

__all__ = [
    # Agents
    "BaseAgent",
    "AgentDefinition",
    "SGRAgent",
    "SGRAutoToolCallingAgent",
    "SGRSOToolCallingAgent",
    "SGRToolCallingAgent",
    "ToolCallingAgent",
    # Tools
    "BaseTool",
    "MCPBaseTool",
    # Factories
    "AgentFactory",
    # Services
    "AgentRegistry",
    "ToolRegistry",
    "PromptLoader",
    "MCP2ToolConverter",
    # Models
    "AgentStatesEnum",
    "ResearchContext",
    "SearchResult",
    "SourceData",
    # Other core modules
    "OpenAIStreamingGenerator",
]
