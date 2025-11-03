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

DEFAULT_AGENTS = [
    AgentDefinition(
        name="sgr_agent",
        display_name="SGR Research Agent",
        description="Deep research agent using SGR framework with planning and reasoning",
        base_class=SGRAgent,
        tools=DEFAULT_TOOLKIT,
    ),
    AgentDefinition(
        name="tool_calling_agent",
        display_name="Tool Calling Agent",
        description="Research agent using native LLM function calling",
        base_class=ToolCallingAgent,
        tools=DEFAULT_TOOLKIT,
    ),
    AgentDefinition(
        name="sgr_tool_calling_agent",
        display_name="SGR Tool Calling Agent",
        description="SGR agent with native function calling for tool selection",
        base_class=SGRToolCallingAgent,
        tools=DEFAULT_TOOLKIT,
    ),
    AgentDefinition(
        name="sgr_auto_tool_calling_agent",
        display_name="SGR Auto Tool Calling Agent",
        description="SGR agent with automatic tool selection",
        base_class=SGRAutoToolCallingAgent,
        tools=DEFAULT_TOOLKIT,
    ),
    AgentDefinition(
        name="sgr_so_tool_calling_agent",
        display_name="SGR Structured Output Agent",
        description="SGR agent using structured outputs for tool calling",
        base_class=SGRSOToolCallingAgent,
        tools=DEFAULT_TOOLKIT,
    ),
]
