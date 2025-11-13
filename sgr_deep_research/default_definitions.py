import sgr_deep_research.core.tools as tools
from sgr_deep_research.core.agent_definition import AgentDefinition
from sgr_deep_research.core.agents.sgr_agent import SGRAgent
from sgr_deep_research.core.agents.sgr_auto_tool_calling_agent import SGRAutoToolCallingAgent
from sgr_deep_research.core.agents.sgr_so_tool_calling_agent import SGRSOToolCallingAgent
from sgr_deep_research.core.agents.sgr_tool_calling_agent import SGRToolCallingAgent
from sgr_deep_research.core.agents.tool_calling_agent import ToolCallingAgent

DEFAULT_TOOLKIT = [
    tools.ClarificationTool,
    tools.GeneratePlanTool,
    tools.AdaptPlanTool,
    tools.FinalAnswerTool,
    tools.WebSearchTool,
    tools.ExtractPageContentTool,
    tools.CreateReportTool,
]


def get_default_agents_definitions() -> dict[str, AgentDefinition]:
    """Get default agent definitions.

    This function creates agent definitions lazily to avoid issues with
    configuration initialization order.

    Returns:
        Dictionary of default agent definitions keyed by agent name
    """
    agents = [
        AgentDefinition(
            name="sgr_agent",
            base_class=SGRAgent,
            tools=DEFAULT_TOOLKIT,
        ),
        AgentDefinition(
            name="tool_calling_agent",
            base_class=ToolCallingAgent,
            tools=DEFAULT_TOOLKIT,
        ),
        AgentDefinition(
            name="sgr_tool_calling_agent",
            base_class=SGRToolCallingAgent,
            tools=DEFAULT_TOOLKIT,
        ),
        AgentDefinition(
            name="sgr_auto_tool_calling_agent",
            base_class=SGRAutoToolCallingAgent,
            tools=DEFAULT_TOOLKIT,
        ),
        AgentDefinition(
            name="sgr_so_tool_calling_agent",
            base_class=SGRSOToolCallingAgent,
            tools=DEFAULT_TOOLKIT,
        ),
    ]
    return {agent.name: agent for agent in agents}
