"""Agent Factory for dynamic agent creation from definitions."""

import logging
from typing import Type, TypeVar

import httpx
from openai import AsyncOpenAI

from sgr_deep_research.core.agent_config import GlobalConfig
from sgr_deep_research.core.agent_definition import AgentDefinition, LLMConfig
from sgr_deep_research.core.agents.definitions import get_default_agents_definitions
from sgr_deep_research.core.base_agent import BaseAgent
from sgr_deep_research.core.services import AgentRegistry, MCP2ToolConverter, ToolRegistry

logger = logging.getLogger(__name__)

Agent = TypeVar("Agent", bound=BaseAgent)


class AgentFactory:
    """Factory for creating agent instances from definitions.

    Use AgentRegistry and ToolRegistry to look up agent classes by name
    and create instances with the appropriate configuration.
    """

    @classmethod
    def _create_client(cls, llm_config: LLMConfig) -> AsyncOpenAI:
        """Create OpenAI client from configuration.

        Args:
            llm_config: LLM configuration

        Returns:
            Configured AsyncOpenAI client
        """
        client_kwargs = {"base_url": llm_config.base_url, "api_key": llm_config.api_key}
        if llm_config.proxy:
            client_kwargs["http_client"] = httpx.AsyncClient(proxy=llm_config.proxy)

        return AsyncOpenAI(**client_kwargs)

    @classmethod
    async def create(cls, agent_def: AgentDefinition, task: str) -> Agent:
        """Create an agent instance from a definition.

        Args:
            agent_def: Agent definition with configuration (classes already resolved)
            task: Task for the agent to execute

        Returns:
            Created agent instance

        Raises:
            ValueError: If agent creation fails
        """
        BaseClass: Type[Agent] | None = (
            AgentRegistry.get(agent_def.base_class) if isinstance(agent_def.base_class, str) else agent_def.base_class
        )
        if BaseClass is None:
            error_msg = (
                f"Agent base class '{agent_def.base_class}' not found in registry.\n"
                f"Available base classes: {', '.join([c.__name__ for c in AgentRegistry.list_items()])}\n"
                f"To fix this issue:\n"
                f"  - Check that '{agent_def.base_class}' is spelled correctly in your configuration\n"
                f"  - Ensure the custom agent classes are imported before creating agents "
                f"(otherwise they won't be registered)"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        mcp_tools = await MCP2ToolConverter.build_tools_from_mcp(agent_def.mcp)

        tools = [*mcp_tools]
        for tool in agent_def.tools:
            if isinstance(tool, str):
                tool_class = ToolRegistry.get(tool)
                if tool_class is None:
                    error_msg = (
                        f"Tool '{tool}' not found in registry.\nAvailable tools: "
                        f"{', '.join([c.__name__ for c in ToolRegistry.list_items()])}\n"
                        f"  - Ensure the custom tool classes are imported before creating agents "
                        f"(otherwise they won't be registered)"
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            else:
                tool_class = tool
            tools.append(tool_class)

        try:
            agent = BaseClass(
                task=task,
                toolkit=tools,
                openai_client=cls._create_client(agent_def.llm),
                llm_config=agent_def.llm,
                execution_config=agent_def.execution,
                prompts_config=agent_def.prompts,
            )
            logger.info(
                f"Created agent '{agent_def.name}' "
                f"using base class '{BaseClass.__name__}' "
                f"with {len(agent.toolkit)} tools"
            )
            return agent
        except Exception as e:
            logger.error(f"Failed to create agent '{agent_def.name}': {e}", exc_info=True)
            raise ValueError(f"Failed to create agent: {e}") from e

    @classmethod
    def get_definitions_list(cls) -> list[AgentDefinition]:
        """Get all agent definitions (default + custom from config).

        Returns:
            List of agent definitions (default agents + custom agents from config)
        """
        config = GlobalConfig()

        all_agents = {agent.name: agent for agent in get_default_agents_definitions()}
        if will_be_rewritten := set(all_agents.keys()).intersection({agent.name for agent in config.agents}):
            logger.warning(f"Custom agents with names {', '.join(will_be_rewritten)} will override default agents.")
        all_agents.update({agent.name: agent for agent in config.agents})
        return list(all_agents.values())
