"""Tests for CreateReportTool.

This module contains tests for CreateReportTool with file generation.
"""

import json
import os
import tempfile
from datetime import datetime
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from sgr_deep_research.core.models import ResearchContext, SourceData
from sgr_deep_research.core.tools.create_report_tool import CreateReportTool


class TestCreateReportTool:
    """Tests for CreateReportTool class."""

    def test_create_report_tool_creation(self):
        """Test creating CreateReportTool with valid data."""
        tool = CreateReportTool(
            reasoning="Ready to create report",
            title="Test Report",
            user_request_language_reference="Research quantum computing",
            content="Report content here",
            confidence="high",
        )
        assert tool.reasoning == "Ready to create report"
        assert tool.title == "Test Report"
        assert tool.content == "Report content here"
        assert tool.confidence == "high"

    def test_create_report_tool_name(self):
        """Test that tool has correct name."""
        assert CreateReportTool.tool_name == "createreporttool"

    def test_create_report_tool_description(self):
        """Test that tool has a description."""
        assert CreateReportTool.description is not None
        assert len(CreateReportTool.description) > 0
        assert "report" in CreateReportTool.description.lower()

    def test_create_report_tool_confidence_levels(self):
        """Test all valid confidence levels."""
        for confidence in ["high", "medium", "low"]:
            tool = CreateReportTool(
                reasoning="Test",
                title="Test",
                user_request_language_reference="Test",
                content="Test",
                confidence=confidence,
            )
            assert tool.confidence == confidence

    def test_create_report_tool_invalid_confidence(self):
        """Test that invalid confidence level raises error."""
        with pytest.raises(ValidationError):
            CreateReportTool(
                reasoning="Test",
                title="Test",
                user_request_language_reference="Test",
                content="Test",
                confidence="invalid",
            )

    def test_create_report_tool_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            CreateReportTool()

    @pytest.mark.asyncio
    async def test_create_report_tool_execution_basic(self):
        """Test CreateReportTool execution creates file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("sgr_deep_research.core.tools.create_report_tool.config") as mock_config:
                mock_config.execution.reports_dir = tmpdir

                tool = CreateReportTool(
                    reasoning="Complete",
                    title="Test Report",
                    user_request_language_reference="Test task",
                    content="This is the report content",
                    confidence="high",
                )

                context = ResearchContext()
                result = await tool(context)

                # Verify JSON result
                result_data = json.loads(result)
                assert result_data["title"] == "Test Report"
                assert result_data["content"] == "This is the report content"
                assert result_data["confidence"] == "high"
                assert result_data["sources_count"] == 0
                assert "filepath" in result_data

                # Verify file was created
                assert os.path.exists(result_data["filepath"])

    @pytest.mark.asyncio
    async def test_create_report_tool_file_content(self):
        """Test that created file has correct content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("sgr_deep_research.core.tools.create_report_tool.config") as mock_config:
                mock_config.execution.reports_dir = tmpdir

                tool = CreateReportTool(
                    reasoning="Complete",
                    title="My Report",
                    user_request_language_reference="Task",
                    content="Report body text",
                    confidence="medium",
                )

                context = ResearchContext()
                result = await tool(context)

                result_data = json.loads(result)
                filepath = result_data["filepath"]

                # Read and verify file content
                with open(filepath, "r", encoding="utf-8") as f:
                    file_content = f.read()

                assert "# My Report" in file_content
                assert "Report body text" in file_content
                assert "Created:" in file_content

    @pytest.mark.asyncio
    async def test_create_report_tool_with_sources(self):
        """Test CreateReportTool includes sources in report."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("sgr_deep_research.core.tools.create_report_tool.config") as mock_config:
                mock_config.execution.reports_dir = tmpdir

                tool = CreateReportTool(
                    reasoning="Complete",
                    title="Report",
                    user_request_language_reference="Task",
                    content="Content with citations [1] and [2]",
                    confidence="high",
                )

                # Add sources to context
                context = ResearchContext()
                context.sources = {
                    "https://example.com/1": SourceData(
                        number=1,
                        title="Source 1",
                        url="https://example.com/1",
                    ),
                    "https://example.com/2": SourceData(
                        number=2,
                        title="Source 2",
                        url="https://example.com/2",
                    ),
                }

                result = await tool(context)
                result_data = json.loads(result)

                assert result_data["sources_count"] == 2

                # Verify sources in file
                with open(result_data["filepath"], "r", encoding="utf-8") as f:
                    file_content = f.read()

                assert "Источники / Sources" in file_content
                assert "Source 1" in file_content
                assert "Source 2" in file_content
                assert "https://example.com/1" in file_content

    @pytest.mark.asyncio
    async def test_create_report_tool_safe_filename(self):
        """Test that CreateReportTool creates safe filenames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("sgr_deep_research.core.tools.create_report_tool.config") as mock_config:
                mock_config.execution.reports_dir = tmpdir

                tool = CreateReportTool(
                    reasoning="Complete",
                    title="Report/with\\invalid:chars?and*stuff",
                    user_request_language_reference="Task",
                    content="Content",
                    confidence="high",
                )

                context = ResearchContext()
                result = await tool(context)
                result_data = json.loads(result)

                filepath = result_data["filepath"]
                filename = os.path.basename(filepath)

                # Verify filename doesn't have invalid characters
                assert "/" not in filename
                assert "\\" not in filename
                assert ":" not in filename[10:]  # Skip timestamp part
                assert "?" not in filename
                assert "*" not in filename

    @pytest.mark.asyncio
    async def test_create_report_tool_filename_length_limit(self):
        """Test that CreateReportTool limits filename length."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("sgr_deep_research.core.tools.create_report_tool.config") as mock_config:
                mock_config.execution.reports_dir = tmpdir

                # Very long title
                long_title = "A" * 200
                tool = CreateReportTool(
                    reasoning="Complete",
                    title=long_title,
                    user_request_language_reference="Task",
                    content="Content",
                    confidence="high",
                )

                context = ResearchContext()
                result = await tool(context)
                result_data = json.loads(result)

                filepath = result_data["filepath"]
                filename = os.path.basename(filepath)

                # Filename should be limited (timestamp + underscore + max 50 chars + .md)
                # Format: YYYYMMDD_HHMMSS_<title>.md
                assert len(filename) < 100

    @pytest.mark.asyncio
    async def test_create_report_tool_word_count(self):
        """Test that CreateReportTool counts words correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("sgr_deep_research.core.tools.create_report_tool.config") as mock_config:
                mock_config.execution.reports_dir = tmpdir

                content = "This is a test report with exactly ten words here"
                tool = CreateReportTool(
                    reasoning="Complete",
                    title="Report",
                    user_request_language_reference="Task",
                    content=content,
                    confidence="high",
                )

                context = ResearchContext()
                result = await tool(context)
                result_data = json.loads(result)

                assert result_data["word_count"] == 10

    @pytest.mark.asyncio
    async def test_create_report_tool_timestamp_format(self):
        """Test that CreateReportTool uses correct timestamp format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("sgr_deep_research.core.tools.create_report_tool.config") as mock_config:
                mock_config.execution.reports_dir = tmpdir

                tool = CreateReportTool(
                    reasoning="Complete",
                    title="Report",
                    user_request_language_reference="Task",
                    content="Content",
                    confidence="high",
                )

                context = ResearchContext()
                result = await tool(context)
                result_data = json.loads(result)

                # Verify timestamp format
                timestamp = result_data["timestamp"]
                # Should be ISO format
                datetime.fromisoformat(timestamp)  # Will raise if invalid

    @pytest.mark.asyncio
    async def test_create_report_tool_creates_directory(self):
        """Test that CreateReportTool creates reports directory if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reports_dir = os.path.join(tmpdir, "reports_subdir")
            assert not os.path.exists(reports_dir)

            with patch("sgr_deep_research.core.tools.create_report_tool.config") as mock_config:
                mock_config.execution.reports_dir = reports_dir

                tool = CreateReportTool(
                    reasoning="Complete",
                    title="Report",
                    user_request_language_reference="Task",
                    content="Content",
                    confidence="high",
                )

                context = ResearchContext()
                await tool(context)

                # Verify directory was created
                assert os.path.exists(reports_dir)
                assert os.path.isdir(reports_dir)

    @pytest.mark.asyncio
    async def test_create_report_tool_markdown_format(self):
        """Test that CreateReportTool creates markdown file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("sgr_deep_research.core.tools.create_report_tool.config") as mock_config:
                mock_config.execution.reports_dir = tmpdir

                tool = CreateReportTool(
                    reasoning="Complete",
                    title="Test Report",
                    user_request_language_reference="Task",
                    content="Content",
                    confidence="high",
                )

                context = ResearchContext()
                result = await tool(context)
                result_data = json.loads(result)

                # Verify file extension
                assert result_data["filepath"].endswith(".md")

    @pytest.mark.asyncio
    async def test_create_report_tool_no_sources(self):
        """Test CreateReportTool with no sources."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("sgr_deep_research.core.tools.create_report_tool.config") as mock_config:
                mock_config.execution.reports_dir = tmpdir

                tool = CreateReportTool(
                    reasoning="Complete",
                    title="Report",
                    user_request_language_reference="Task",
                    content="Content without citations",
                    confidence="low",
                )

                context = ResearchContext()
                result = await tool(context)
                result_data = json.loads(result)

                assert result_data["sources_count"] == 0

                # File should not have sources section
                with open(result_data["filepath"], "r", encoding="utf-8") as f:
                    file_content = f.read()

                assert "Источники / Sources" not in file_content

    @pytest.mark.asyncio
    async def test_create_report_tool_language_reference_preserved(self):
        """Test that user_request_language_reference is used correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("sgr_deep_research.core.tools.create_report_tool.config") as mock_config:
                mock_config.execution.reports_dir = tmpdir

                tool = CreateReportTool(
                    reasoning="Complete",
                    title="Report",
                    user_request_language_reference="Исследуйте квантовые компьютеры",
                    content="Russian content here",
                    confidence="high",
                )

                context = ResearchContext()
                result = await tool(context)
                result_data = json.loads(result)

                # Just verify it doesn't crash and creates report
                assert result_data["title"] == "Report"
                assert os.path.exists(result_data["filepath"])
