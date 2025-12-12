from sgr_agent_core.base_tool import BaseTool, MCPBaseTool
from sgr_agent_core.next_step_tool import NextStepToolsBuilder, NextStepToolStub
from sgr_agent_core.tools.adapt_plan_tool import AdaptPlanTool
from sgr_agent_core.tools.clarification_tool import ClarificationTool
from sgr_agent_core.tools.create_report_tool import CreateReportTool
from sgr_agent_core.tools.extract_page_content_tool import ExtractPageContentTool
from sgr_agent_core.tools.final_answer_tool import FinalAnswerTool
from sgr_agent_core.tools.generate_plan_tool import GeneratePlanTool
from sgr_agent_core.tools.reasoning_tool import ReasoningTool
from sgr_agent_core.tools.web_search_tool import WebSearchTool

# Tool lists for backward compatibility
system_agent_tools = [
    ClarificationTool,
    GeneratePlanTool,
    AdaptPlanTool,
    FinalAnswerTool,
    ReasoningTool,
]

research_agent_tools = [
    WebSearchTool,
    ExtractPageContentTool,
    CreateReportTool,
]

__all__ = [
    # Base classes
    "BaseTool",
    "MCPBaseTool",
    "NextStepToolStub",
    "NextStepToolsBuilder",
    # Individual tools
    "ClarificationTool",
    "GeneratePlanTool",
    "WebSearchTool",
    "ExtractPageContentTool",
    "AdaptPlanTool",
    "CreateReportTool",
    "FinalAnswerTool",
    "ReasoningTool",
    # Tool lists
    "NextStepToolStub",
    "NextStepToolsBuilder",
    # Tool Collections
    "system_agent_tools",
    "research_agent_tools",
]
