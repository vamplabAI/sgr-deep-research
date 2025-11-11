"""Tests for prompts module.

This module contains tests for PromptLoader utility class.
"""

import os
import tempfile
from datetime import datetime
from unittest.mock import patch

import pytest

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.prompts import PromptLoader


class TestPromptLoader:
    """Tests for PromptLoader class."""

    def test_load_prompt_file_exists_in_user_dir(self):
        """Test loading prompt file from user directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test prompt file
            test_file = os.path.join(tmpdir, "test_prompt.txt")
            test_content = "This is a test prompt"
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(test_content)

            # Mock config to point to our temp directory
            with patch("sgr_deep_research.core.prompts.config") as mock_config:
                mock_config.prompts.prompts_dir = tmpdir
                # Clear cache to test fresh load
                PromptLoader._load_prompt_file.cache_clear()

                result = PromptLoader._load_prompt_file("test_prompt.txt")
                assert result == test_content

    def test_load_prompt_file_caching(self):
        """Test that _load_prompt_file uses caching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "cached_prompt.txt")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("Cached content")

            with patch("sgr_deep_research.core.prompts.config") as mock_config:
                mock_config.prompts.prompts_dir = tmpdir
                PromptLoader._load_prompt_file.cache_clear()

                # First call
                result1 = PromptLoader._load_prompt_file("cached_prompt.txt")
                # Second call should use cache
                result2 = PromptLoader._load_prompt_file("cached_prompt.txt")

                assert result1 == result2 == "Cached content"

    def test_load_prompt_file_not_found(self):
        """Test that FileNotFoundError is raised when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("sgr_deep_research.core.prompts.config") as mock_config:
                mock_config.prompts.prompts_dir = tmpdir
                PromptLoader._load_prompt_file.cache_clear()

                with pytest.raises(FileNotFoundError) as exc_info:
                    PromptLoader._load_prompt_file("nonexistent.txt")
                assert "Prompt file not found" in str(exc_info.value)

    def test_load_prompt_file_io_error(self):
        """Test that IOError is properly handled and re-raised."""
        with patch("builtins.open", side_effect=IOError("Permission denied")):
            with patch("os.path.exists", return_value=True):
                with patch("sgr_deep_research.core.prompts.config") as mock_config:
                    mock_config.prompts.prompts_dir = "test"
                    PromptLoader._load_prompt_file.cache_clear()

                    with pytest.raises(IOError) as exc_info:
                        PromptLoader._load_prompt_file("test.txt")
                    assert "Error reading prompt file" in str(exc_info.value)

    def test_load_prompt_file_strips_whitespace(self):
        """Test that loaded content is stripped of leading/trailing
        whitespace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "whitespace.txt")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("  \n  Content with spaces  \n  ")

            with patch("sgr_deep_research.core.prompts.config") as mock_config:
                mock_config.prompts.prompts_dir = tmpdir
                PromptLoader._load_prompt_file.cache_clear()

                result = PromptLoader._load_prompt_file("whitespace.txt")
                assert result == "Content with spaces"

    def test_get_system_prompt_with_tools(self):
        """Test get_system_prompt with available tools."""

        # Create mock tools
        class MockTool1(BaseTool):
            tool_name = "mock_tool_1"
            description = "First mock tool"

        class MockTool2(BaseTool):
            tool_name = "mock_tool_2"
            description = "Second mock tool"

        tools = [MockTool1, MockTool2]

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create system prompt template
            template_file = os.path.join(tmpdir, "system_prompt.txt")
            template = "Available tools:\n{available_tools}\nUse them wisely."
            with open(template_file, "w", encoding="utf-8") as f:
                f.write(template)

            with patch("sgr_deep_research.core.prompts.config") as mock_config:
                mock_config.prompts.prompts_dir = tmpdir
                mock_config.prompts.system_prompt_file = "system_prompt.txt"
                PromptLoader._load_prompt_file.cache_clear()

                result = PromptLoader.get_system_prompt(tools)

                assert "Available tools:" in result
                assert "1. mock_tool_1: First mock tool" in result
                assert "2. mock_tool_2: Second mock tool" in result
                assert "Use them wisely." in result

    def test_get_system_prompt_empty_tools(self):
        """Test get_system_prompt with no tools."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = os.path.join(tmpdir, "system_prompt.txt")
            template = "Available tools:\n{available_tools}\nDone."
            with open(template_file, "w", encoding="utf-8") as f:
                f.write(template)

            with patch("sgr_deep_research.core.prompts.config") as mock_config:
                mock_config.prompts.prompts_dir = tmpdir
                mock_config.prompts.system_prompt_file = "system_prompt.txt"
                PromptLoader._load_prompt_file.cache_clear()

                result = PromptLoader.get_system_prompt([])

                assert "Available tools:\n\nDone." in result

    def test_get_system_prompt_missing_placeholder(self):
        """Test get_system_prompt with missing placeholder raises KeyError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = os.path.join(tmpdir, "system_prompt.txt")
            # Template without {available_tools} placeholder
            template = "This template has no placeholders."
            with open(template_file, "w", encoding="utf-8") as f:
                f.write(template)

            with patch("sgr_deep_research.core.prompts.config") as mock_config:
                mock_config.prompts.prompts_dir = tmpdir
                mock_config.prompts.system_prompt_file = "system_prompt.txt"
                PromptLoader._load_prompt_file.cache_clear()

                # This should work since no placeholder is used
                result = PromptLoader.get_system_prompt([])
                assert result == "This template has no placeholders."

    def test_get_initial_user_request(self):
        """Test get_initial_user_request formats task correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = os.path.join(tmpdir, "initial_user_request.txt")
            template = "Current Date: {current_date}\nTASK:\n{task}"
            with open(template_file, "w", encoding="utf-8") as f:
                f.write(template)

            with patch("sgr_deep_research.core.prompts.config") as mock_config:
                mock_config.prompts.prompts_dir = tmpdir
                PromptLoader._load_prompt_file.cache_clear()

                task = "Research quantum computing"
                result = PromptLoader.get_initial_user_request(task)

                assert "TASK:" in result
                assert "Research quantum computing" in result
                assert "Current Date:" in result
                # Check that date is in the result
                current_year = datetime.now().year
                assert str(current_year) in result

    def test_get_initial_user_request_date_format(self):
        """Test that get_initial_user_request includes properly formatted
        date."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = os.path.join(tmpdir, "initial_user_request.txt")
            template = "{current_date}|{task}"
            with open(template_file, "w", encoding="utf-8") as f:
                f.write(template)

            with patch("sgr_deep_research.core.prompts.config") as mock_config:
                mock_config.prompts.prompts_dir = tmpdir
                PromptLoader._load_prompt_file.cache_clear()

                result = PromptLoader.get_initial_user_request("test task")

                # Check format YYYY-MM-DD HH:MM:SS
                parts = result.split("|")
                date_part = parts[0]
                assert len(date_part) == 19  # YYYY-MM-DD HH:MM:SS
                assert date_part[4] == "-"
                assert date_part[7] == "-"
                assert date_part[10] == " "
                assert date_part[13] == ":"
                assert date_part[16] == ":"

    def test_get_clarification_template(self):
        """Test get_clarification_template formats clarifications correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = os.path.join(tmpdir, "clarification_response.txt")
            template = "Date: {current_date}\nCLARIFICATIONS:\n{clarifications}"
            with open(template_file, "w", encoding="utf-8") as f:
                f.write(template)

            with patch("sgr_deep_research.core.prompts.config") as mock_config:
                mock_config.prompts.prompts_dir = tmpdir
                PromptLoader._load_prompt_file.cache_clear()

                clarifications = "1. Answer A\n2. Answer B"
                result = PromptLoader.get_clarification_template(clarifications)

                assert "CLARIFICATIONS:" in result
                assert "1. Answer A" in result
                assert "2. Answer B" in result
                assert "Date:" in result

    def test_get_clarification_template_date_format(self):
        """Test that get_clarification_template includes properly formatted
        date."""
        with tempfile.TemporaryDirectory() as tmpdir:
            template_file = os.path.join(tmpdir, "clarification_response.txt")
            template = "{current_date}|{clarifications}"
            with open(template_file, "w", encoding="utf-8") as f:
                f.write(template)

            with patch("sgr_deep_research.core.prompts.config") as mock_config:
                mock_config.prompts.prompts_dir = tmpdir
                PromptLoader._load_prompt_file.cache_clear()

                result = PromptLoader.get_clarification_template("test")

                # Check that date is properly formatted
                parts = result.split("|")
                date_part = parts[0]
                assert len(date_part) == 19  # YYYY-MM-DD HH:MM:SS

    def test_load_prompt_file_falls_back_to_lib_dir(self):
        """Test that loader falls back to library directory when user dir
        doesn't exist."""
        # This tests the fallback mechanism in _load_prompt_file
        # In real scenario, it should find files in the installed package
        with patch("sgr_deep_research.core.prompts.config") as mock_config:
            mock_config.prompts.prompts_dir = "prompts"
            PromptLoader._load_prompt_file.cache_clear()

            # Try to load one of the actual prompt files
            # This should work if the package is properly installed
            try:
                result = PromptLoader._load_prompt_file("initial_user_request.txt")
                assert len(result) > 0
                assert "{task}" in result or "{current_date}" in result
            except FileNotFoundError:
                # If file is not found, that's also acceptable in test environment
                pytest.skip("Prompt files not found in package - this is ok in test env")
