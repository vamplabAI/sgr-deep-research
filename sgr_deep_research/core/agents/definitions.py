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
        display_name="SGR Research Agent",
        description="Deep research agent using SGR framework with planning and reasoning",
        base_class=SGRResearchAgent,
        tools=DEFAULT_TOOLKIT,
    ),
    AgentDefinition(
        name="tool_calling_agent",
        display_name="Tool Calling Agent",
        description="Research agent using native LLM function calling",
        base_class=ToolCallingResearchAgent,
        tools=DEFAULT_TOOLKIT,
    ),
    AgentDefinition(
        name="sgr_tool_calling_agent",
        display_name="SGR Tool Calling Agent",
        description="SGR agent with native function calling for tool selection",
        base_class=SGRToolCallingResearchAgent,
        tools=DEFAULT_TOOLKIT,
    ),
    AgentDefinition(
        name="sgr_auto_tool_calling_agent",
        display_name="SGR Auto Tool Calling Agent",
        description="SGR agent with automatic tool selection",
        base_class=SGRAutoToolCallingResearchAgent,
        tools=DEFAULT_TOOLKIT,
    ),
    AgentDefinition(
        name="sgr_so_tool_calling_agent",
        display_name="SGR Structured Output Agent",
        description="SGR agent using structured outputs for tool calling",
        base_class=SGRSOToolCallingResearchAgent,
        tools=DEFAULT_TOOLKIT,
    ),
]
