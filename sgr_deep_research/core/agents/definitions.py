import sgr_deep_research.core.tools as tools
from sgr_deep_research.core.agent_definition import AgentDefinition
from sgr_deep_research.core.agents.sgr_agent import SGRResearchAgent
from sgr_deep_research.core.agents.sgr_auto_tools_agent import SGRAutoToolCallingResearchAgent
from sgr_deep_research.core.agents.sgr_so_tools_agent import SGRSOToolCallingResearchAgent
from sgr_deep_research.core.agents.sgr_tools_agent import SGRToolCallingResearchAgent
from sgr_deep_research.core.agents.tools_agent import ToolCallingResearchAgent

DEFAULT_TOOLKIT = [
    tools.ClarificationTool,
    tools.GeneratePlanTool,
    tools.AdaptPlanTool,
    tools.FinalAnswerTool,
    tools.WebSearchTool,
    tools.ExtractPageContentTool,
    tools.CreateReportTool,
]

DEFAULT_AGENTS = [
    AgentDefinition(
        name="sgr_agent",
        base_class=SGRResearchAgent,
        tools=DEFAULT_TOOLKIT,
    ),
    AgentDefinition(
        name="tool_calling_agent",
        base_class=ToolCallingResearchAgent,
        tools=DEFAULT_TOOLKIT,
    ),
    AgentDefinition(
        name="sgr_tool_calling_agent",
        base_class=SGRToolCallingResearchAgent,
        tools=DEFAULT_TOOLKIT,
    ),
    AgentDefinition(
        name="sgr_auto_tool_calling_agent",
        base_class=SGRAutoToolCallingResearchAgent,
        tools=DEFAULT_TOOLKIT,
    ),
    AgentDefinition(
        name="sgr_so_tool_calling_agent",
        base_class=SGRSOToolCallingResearchAgent,
        tools=DEFAULT_TOOLKIT,
    ),
]
