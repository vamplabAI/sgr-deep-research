"""Agent Factory for dynamic agent creation from definitions."""

import logging
from typing import Type, TypeVar

from sgr_deep_research.agent_settings import AgentDefinition, get_agents_config
from sgr_deep_research.core.agents.definitions import DEFAULT_AGENTS
from sgr_deep_research.core.base_agent import BaseAgent
from sgr_deep_research.core.registry import AgentRegistry, ToolRegistry

logger = logging.getLogger(__name__)

Agent = TypeVar("Agent", bound=BaseAgent)


class AgentFactory:
    """Factory for creating agent instances from definitions.

    Uses AgentRegistry to look up agent classes by name and creates
    instances with the appropriate configuration.
    """

    @classmethod
    def create(cls, agent_def: AgentDefinition, task: str) -> BaseAgent:
        """Create an agent instance from a definition.

        Args:
            agent_def: Agent definition with configuration
            task: Task for the agent to execute

        Returns:
            Created agent instance

        Raises:
            ValueError: If base class is not found or agent creation fails
        """
        BaseClass: Type[Agent] = AgentRegistry.get(agent_def.base_class)
        if BaseClass is None:
            raise ValueError(
                f"Base class '{agent_def.base_class}' not found. "
                f"Available: {[c.__name__ for c in AgentRegistry.list_items()]}"
            )
        tools = ToolRegistry.resolve(agent_def.tools) if agent_def.tools else []

        try:
            agent = BaseClass(
                task=task,
                toolkit=tools,
                openai_config=agent_def.openai,
                prompts_config=agent_def.prompts,
                **agent_def.config.model_dump(),
            )
            logger.info(
                f"Created agent '{agent_def.name}' "
                f"using base class '{agent_def.base_class}' "
                f"with {len(tools)} tools"
            )
            return agent
        except Exception as e:
            logger.error(f"Failed to create agent '{agent_def.name}': {e}")
            raise ValueError(f"Failed to create agent: {e}") from e

    @classmethod
    def get_definitions(cls) -> list[AgentDefinition]:
        """Get all agent definitions (default + custom from config).

        Returns:
            List of agent definitions (default agents + custom agents from config)
        """
        config = get_agents_config()
        custom_agents = config.agents

        # Merge default and custom agents (custom can override default by name)
        all_agents = {agent.name: agent for agent in DEFAULT_AGENTS}
        all_agents.update({agent.name: agent for agent in custom_agents})

        return list(all_agents.values())
