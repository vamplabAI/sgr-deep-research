# Base tool class
from sgr_deep_research.core.base_tool import BaseTool

# System tools
from sgr_deep_research.tools.clarification_tool import ClarificationTool
from sgr_deep_research.tools.generate_plan_tool import GeneratePlanTool
from sgr_deep_research.tools.adapt_plan_tool import AdaptPlanTool
from sgr_deep_research.tools.agent_completion_tool import AgentCompletionTool
from sgr_deep_research.tools.reasoning_tool import ReasoningTool

# Research tools
from sgr_deep_research.tools.web_search_tool import WebSearchTool
from sgr_deep_research.tools.create_report_tool import CreateReportTool

# SGR framework tools
from sgr_deep_research.tools.next_step_tools import (
    NextStepToolsBuilder,
    NextStepToolStub,
)

# Tool collections
system_agent_tools = [
    ClarificationTool,
    GeneratePlanTool,
    AdaptPlanTool,
    AgentCompletionTool,
    ReasoningTool,
]

research_agent_tools = [
    WebSearchTool,
    CreateReportTool,
]

__all__ = [
    # Base
    "BaseTool",
    # System tools
    "ClarificationTool",
    "GeneratePlanTool",
    "AdaptPlanTool",
    "AgentCompletionTool",
    "ReasoningTool",
    # Research tools
    "WebSearchTool",
    "CreateReportTool",
    # SGR framework
    "NextStepToolStub",
    "NextStepToolsBuilder",
    # Collections
    "system_agent_tools",
    "research_agent_tools",
]
