from pathlib import Path

import sgr_agent_core.tools as tools
from sgr_agent_core.agent_definition import AgentDefinition, PromptsConfig
from sgr_agent_core.agents import ResearchSGRAgent, ResearchSGRToolCallingAgent, ResearchToolCallingAgent

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
            base_class=ResearchSGRAgent,
            tools=DEFAULT_TOOLKIT,
            prompts=PromptsConfig(system_prompt_file=Path("sgr_agent_core/prompts/research_system_prompt.txt")),
        ),
        AgentDefinition(
            name="tool_calling_agent",
            base_class=ResearchToolCallingAgent,
            tools=DEFAULT_TOOLKIT,
            prompts=PromptsConfig(system_prompt_file=Path("sgr_agent_core/prompts/research_system_prompt.txt")),
        ),
        AgentDefinition(
            name="sgr_tool_calling_agent",
            base_class=ResearchSGRToolCallingAgent,
            tools=DEFAULT_TOOLKIT,
            prompts=PromptsConfig(system_prompt_file=Path("sgr_agent_core/prompts/research_system_prompt.txt")),
        ),
    ]
    return {agent.name: agent for agent in agents}
