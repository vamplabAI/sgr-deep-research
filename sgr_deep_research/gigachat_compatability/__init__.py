"""GigaChat compatibility modules for SGR Agent Core."""

# Imports from sgr_deep_research.core
from sgr_deep_research.core.agent_config import GlobalConfig
from sgr_deep_research.core.agent_definition import ExecutionConfig, LLMConfig, PromptsConfig
from sgr_deep_research.core.base_agent import BaseAgent
from sgr_deep_research.core.services.tavily_search import TavilySearchService

from sgr_deep_research.gigachat_compatability.models import AgentStatesEnum, ResearchContextCounted, SearchResult, SourceData
from sgr_deep_research.gigachat_compatability.base_agent import BaseAgent_functional
from sgr_deep_research.gigachat_compatability.base_tool import BaseTool_functional
from sgr_deep_research.gigachat_compatability.agents.tool_calling_agent import ToolCallingAgent_functional
from sgr_deep_research.gigachat_compatability.tools.adapt_plan_tool import AdaptPlanTool_functional
from sgr_deep_research.gigachat_compatability.tools.clarification_tool import ClarificationTool_functional
from sgr_deep_research.gigachat_compatability.tools.create_report_tool import CreateReportTool_functional
from sgr_deep_research.gigachat_compatability.tools.extract_page_content_tool import ExtractPageContentTool_functional
from sgr_deep_research.gigachat_compatability.tools.final_answer_tool import FinalAnswerTool_functional
from sgr_deep_research.gigachat_compatability.tools.generate_plan_tool import GeneratePlanTool_functional
from sgr_deep_research.gigachat_compatability.tools.reasoning_tool import ReasoningTool_functional
from sgr_deep_research.gigachat_compatability.tools.web_search_tool import WebSearchTool_functional

__all__ = [
    # Agents
    "BaseAgent_functional",
    "ToolCallingAgent_functional",
    # Tools
    "AdaptPlanTool_functional",
    "BaseTool_functional",
    "ClarificationTool_functional",
    "CreateReportTool_functional",
    "ExtractPageContentTool_functional",
    "FinalAnswerTool_functional",
    "GeneratePlanTool_functional",
    "ReasoningTool_functional",
    "WebSearchTool_functional",
]
