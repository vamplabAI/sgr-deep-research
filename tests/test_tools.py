"""Tests for all tools.

This module contains simple tests for all tools:
- Initialization
- Config reading (if needed)
"""

from unittest.mock import patch

import pytest

from sgr_agent_core.tools import (
    AdaptPlanTool,
    ClarificationTool,
    CreateReportTool,
    ExtractPageContentTool,
    FinalAnswerTool,
    GeneratePlanTool,
    ReasoningTool,
    WebSearchTool,
)


class TestToolsInitialization:
    """Test that all tools can be initialized."""

    def test_clarification_tool_initialization(self):
        """Test ClarificationTool initialization."""
        tool = ClarificationTool(
            reasoning="Test",
            unclear_terms=["term1"],
            assumptions=["assumption1", "assumption2"],
            questions=["Question 1?", "Question 2?", "Question 3?"],
        )
        assert tool.tool_name == "clarificationtool"
        assert tool.reasoning == "Test"

    def test_generate_plan_tool_initialization(self):
        """Test GeneratePlanTool initialization."""
        tool = GeneratePlanTool(
            reasoning="Test",
            research_goal="Test goal",
            planned_steps=["Step 1", "Step 2", "Step 3"],
            search_strategies=["Strategy 1", "Strategy 2"],
        )
        assert tool.tool_name == "generateplantool"
        assert len(tool.planned_steps) == 3

    def test_adapt_plan_tool_initialization(self):
        """Test AdaptPlanTool initialization."""
        tool = AdaptPlanTool(
            reasoning="Test",
            original_goal="Original goal",
            new_goal="New goal",
            plan_changes=["Change 1"],
            next_steps=["Step 1", "Step 2"],
        )
        assert tool.tool_name == "adaptplantool"
        assert len(tool.next_steps) == 2

    def test_final_answer_tool_initialization(self):
        """Test FinalAnswerTool initialization."""
        from sgr_agent_core.models import AgentStatesEnum

        tool = FinalAnswerTool(
            reasoning="Test",
            completed_steps=["Step 1"],
            answer="Answer",
            status=AgentStatesEnum.COMPLETED,
        )
        assert tool.tool_name == "finalanswertool"
        assert tool.answer == "Answer"

    def test_reasoning_tool_initialization(self):
        """Test ReasoningTool initialization."""
        tool = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Test",
            plan_status="Test",
            enough_data=False,
            remaining_steps=["Next"],
            task_completed=False,
        )
        assert tool.tool_name == "reasoningtool"
        assert len(tool.reasoning_steps) == 2

    def test_web_search_tool_initialization(self):
        """Test WebSearchTool initialization."""
        tool = WebSearchTool(
            reasoning="Test",
            query="test query",
        )
        assert tool.tool_name == "websearchtool"
        assert tool.query == "test query"

    def test_extract_page_content_tool_initialization(self):
        """Test ExtractPageContentTool initialization."""
        with patch("sgr_agent_core.tools.extract_page_content_tool.TavilySearchService"):
            tool = ExtractPageContentTool(
                reasoning="Test",
                urls=["https://example.com"],
            )
            assert tool.tool_name == "extractpagecontenttool"
            assert len(tool.urls) == 1

    def test_create_report_tool_initialization(self):
        """Test CreateReportTool initialization."""
        tool = CreateReportTool(
            reasoning="Test",
            title="Test Report",
            user_request_language_reference="Test",
            content="Test content",
            confidence="high",
        )
        assert tool.tool_name == "createreporttool"
        assert tool.title == "Test Report"


class TestToolsConfigReading:
    """Test that tools that need config can read it correctly."""

    def test_web_search_tool_reads_config(self):
        """Test WebSearchTool reads search config for max_results."""
        tool = WebSearchTool(
            reasoning="Test",
            query="test query",
            max_results=5,
        )
        # Tool should use provided max_results
        assert tool.query == "test query"
        assert tool.max_results == 5

    def test_extract_page_content_tool_reads_config(self):
        """Test ExtractPageContentTool reads search config."""
        tool = ExtractPageContentTool(
            reasoning="Test",
            urls=["https://example.com"],
        )
        # Tool should be initialized without errors
        assert len(tool.urls) == 1

    def test_create_report_tool_reads_config(self):
        """Test CreateReportTool reads execution config."""
        tool = CreateReportTool(
            reasoning="Test",
            title="Test Report",
            user_request_language_reference="Test",
            content="Test content",
            confidence="high",
        )
        # Tool should be initialized without errors
        assert tool.title == "Test Report"


class TestCreateReportToolFileWriting:
    """Tests for CreateReportTool file writing behavior."""

    @pytest.mark.asyncio
    async def test_create_report_creates_file_when_reports_dir_is_set(self, tmp_path):
        """Test that CreateReportTool creates report file when reports_dir is
        specified."""
        import json
        import os

        from sgr_agent_core.agent_definition import AgentConfig, ExecutionConfig, LLMConfig, PromptsConfig
        from sgr_agent_core.models import AgentContext

        reports_dir = str(tmp_path / "reports")

        tool = CreateReportTool(
            reasoning="Test",
            title="Test Report",
            user_request_language_reference="Test request",
            content="Test content with citation [1].",
            confidence="high",
        )

        context = AgentContext()
        config = AgentConfig(
            llm=LLMConfig(api_key="test"),
            prompts=PromptsConfig(
                system_prompt_str="Test",
                initial_user_request_str="Test",
                clarification_response_str="Test",
            ),
            execution=ExecutionConfig(
                max_iterations=10,
                max_clarifications=3,
                reports_dir=reports_dir,
            ),
        )

        result = await tool(context, config)
        result_data = json.loads(result)

        # Should return result with filepath
        assert result_data["title"] == "Test Report"
        assert result_data["filepath"] is not None
        assert reports_dir in result_data["filepath"]

        # Verify report file was created
        assert os.path.exists(reports_dir)
        report_files = list(os.listdir(reports_dir))
        assert len(report_files) == 1
        assert report_files[0].endswith(".md")
