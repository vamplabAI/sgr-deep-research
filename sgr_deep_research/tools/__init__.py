# Base tool class
from sgr_deep_research.core.base_tool import BaseTool

# Tools registry
from sgr_deep_research.core.tools_registry import ToolsRegistry, tool

# Import all tools to trigger registration
from sgr_deep_research.tools.clarification_tool import ClarificationTool
from sgr_deep_research.tools.generate_plan_tool import GeneratePlanTool
from sgr_deep_research.tools.adapt_plan_tool import AdaptPlanTool
from sgr_deep_research.tools.agent_completion_tool import AgentCompletionTool
from sgr_deep_research.tools.reasoning_tool import ReasoningTool
from sgr_deep_research.tools.web_search_tool import WebSearchTool
from sgr_deep_research.tools.create_report_tool import CreateReportTool

# SGR framework tools
from sgr_deep_research.tools.next_step_tools import (
    NextStepToolsBuilder,
    NextStepToolStub,
)

# Tool collections using registry
system_agent_tools = ToolsRegistry.get_system_tools()
research_agent_tools = ToolsRegistry.get_research_tools()

__all__ = [
    # Base
    "BaseTool",
    # Registry
    "ToolsRegistry", 
    "tool",
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
    # Collections (now from registry)
    "system_agent_tools",
    "research_agent_tools",
]