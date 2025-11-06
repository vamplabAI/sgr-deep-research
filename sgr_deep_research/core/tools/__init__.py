from sgr_deep_research.core.base_tool import (
    BaseTool,
    MCPBaseTool,
)
from sgr_deep_research.core.next_step_tool import (
    NextStepToolsBuilder,
    NextStepToolStub,
)
from sgr_deep_research.core.tools.adapt_plan_tool import AdaptPlanTool
from sgr_deep_research.core.tools.clarification_tool import ClarificationTool
from sgr_deep_research.core.tools.create_report_tool import CreateReportTool
from sgr_deep_research.core.tools.extract_page_content_tool import ExtractPageContentTool
from sgr_deep_research.core.tools.final_answer_tool import FinalAnswerTool
from sgr_deep_research.core.tools.find_files_fast_tool import FindFilesFastTool
from sgr_deep_research.core.tools.generate_plan_tool import GeneratePlanTool
from sgr_deep_research.core.tools.get_current_directory_tool import GetCurrentDirectoryTool
from sgr_deep_research.core.tools.get_system_paths_tool import GetSystemPathsTool
from sgr_deep_research.core.tools.list_directory_tool import ListDirectoryTool
from sgr_deep_research.core.tools.read_file_tool import ReadFileTool
from sgr_deep_research.core.tools.reasoning_tool import ReasoningTool
from sgr_deep_research.core.tools.search_in_files_tool import SearchInFilesTool
from sgr_deep_research.core.tools.web_search_tool import WebSearchTool

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

file_system_tools = [
    GetCurrentDirectoryTool,
    GetSystemPathsTool,
    ReadFileTool,
    ListDirectoryTool,
    SearchInFilesTool,
    FindFilesFastTool,
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
    "GetCurrentDirectoryTool",
    "GetSystemPathsTool",
    "ReadFileTool",
    "ListDirectoryTool",
    "SearchInFilesTool",
    "FindFilesFastTool",
    # Tool Collections
    "system_agent_tools",
    "research_agent_tools",
    "file_system_tools",
]
