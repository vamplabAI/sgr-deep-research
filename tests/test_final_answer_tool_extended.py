"""Extended tests for FinalAnswerTool.

This module contains comprehensive tests for the FinalAnswerTool,
covering validation, execution, state transitions, and JSON output.
"""

import json

import pytest
from pydantic import ValidationError

from sgr_deep_research.core.models import AgentStatesEnum, ResearchContext
from sgr_deep_research.core.tools import FinalAnswerTool


class TestFinalAnswerToolValidation:
    """Test validation rules for FinalAnswerTool fields."""

    def test_completed_steps_min_length(self):
        """Test validation fails when completed_steps is empty."""
        with pytest.raises(ValidationError) as exc_info:
            FinalAnswerTool(
                reasoning="Task completed",
                completed_steps=[],
                answer="Final answer",
                status=AgentStatesEnum.COMPLETED,
            )
        assert "completed_steps" in str(exc_info.value)

    def test_completed_steps_max_length(self):
        """Test validation fails when completed_steps exceeds 5 items."""
        with pytest.raises(ValidationError) as exc_info:
            FinalAnswerTool(
                reasoning="Task completed",
                completed_steps=["Step 1", "Step 2", "Step 3", "Step 4", "Step 5", "Step 6"],
                answer="Final answer",
                status=AgentStatesEnum.COMPLETED,
            )
        assert "completed_steps" in str(exc_info.value)

    def test_completed_steps_boundary_values(self):
        """Test completed_steps with boundary values (1 and 5 items)."""
        # Test with 1 item (min boundary)
        tool1 = FinalAnswerTool(
            reasoning="Task completed",
            completed_steps=["Step 1"],
            answer="Final answer",
            status=AgentStatesEnum.COMPLETED,
        )
        assert len(tool1.completed_steps) == 1

        # Test with 5 items (max boundary)
        tool5 = FinalAnswerTool(
            reasoning="Task completed",
            completed_steps=["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"],
            answer="Final answer",
            status=AgentStatesEnum.COMPLETED,
        )
        assert len(tool5.completed_steps) == 5

    def test_status_completed(self):
        """Test that status can be COMPLETED."""
        tool = FinalAnswerTool(
            reasoning="Task completed",
            completed_steps=["Step 1"],
            answer="Final answer",
            status=AgentStatesEnum.COMPLETED,
        )
        assert tool.status == AgentStatesEnum.COMPLETED

    def test_status_failed(self):
        """Test that status can be FAILED."""
        tool = FinalAnswerTool(
            reasoning="Task failed",
            completed_steps=["Step 1"],
            answer="Could not complete",
            status=AgentStatesEnum.FAILED,
        )
        assert tool.status == AgentStatesEnum.FAILED

    def test_status_invalid(self):
        """Test that invalid status values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            FinalAnswerTool(
                reasoning="Task completed",
                completed_steps=["Step 1"],
                answer="Final answer",
                status="invalid_status",
            )
        assert "status" in str(exc_info.value)

    def test_status_wrong_enum_value(self):
        """Test that other AgentStatesEnum values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            FinalAnswerTool(
                reasoning="Task completed",
                completed_steps=["Step 1"],
                answer="Final answer",
                status=AgentStatesEnum.RESEARCHING,
            )
        assert "status" in str(exc_info.value)

    def test_required_fields(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            FinalAnswerTool()

    def test_reasoning_required(self):
        """Test that reasoning field is required."""
        with pytest.raises(ValidationError) as exc_info:
            FinalAnswerTool(
                completed_steps=["Step 1"],
                answer="Final answer",
                status=AgentStatesEnum.COMPLETED,
            )
        assert "reasoning" in str(exc_info.value)

    def test_answer_required(self):
        """Test that answer field is required."""
        with pytest.raises(ValidationError) as exc_info:
            FinalAnswerTool(
                reasoning="Task completed",
                completed_steps=["Step 1"],
                status=AgentStatesEnum.COMPLETED,
            )
        assert "answer" in str(exc_info.value)


class TestFinalAnswerToolExecution:
    """Test execution behavior of FinalAnswerTool."""

    @pytest.mark.asyncio
    async def test_execution_returns_string(self):
        """Test that execution returns a string."""
        tool = FinalAnswerTool(
            reasoning="Task completed",
            completed_steps=["Step 1"],
            answer="Final answer",
            status=AgentStatesEnum.COMPLETED,
        )
        context = ResearchContext()
        result = await tool(context)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_execution_returns_valid_json(self):
        """Test that execution returns valid JSON."""
        tool = FinalAnswerTool(
            reasoning="Task completed",
            completed_steps=["Step 1"],
            answer="Final answer",
            status=AgentStatesEnum.COMPLETED,
        )
        context = ResearchContext()
        result = await tool(context)

        data = json.loads(result)
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_execution_sets_context_state_completed(self):
        """Test that execution sets context state to COMPLETED."""
        tool = FinalAnswerTool(
            reasoning="Task completed",
            completed_steps=["Step 1"],
            answer="Final answer",
            status=AgentStatesEnum.COMPLETED,
        )
        context = ResearchContext()
        await tool(context)

        assert context.state == AgentStatesEnum.COMPLETED

    @pytest.mark.asyncio
    async def test_execution_sets_context_state_failed(self):
        """Test that execution sets context state to FAILED."""
        tool = FinalAnswerTool(
            reasoning="Task failed",
            completed_steps=["Step 1"],
            answer="Could not complete",
            status=AgentStatesEnum.FAILED,
        )
        context = ResearchContext()
        await tool(context)

        assert context.state == AgentStatesEnum.FAILED

    @pytest.mark.asyncio
    async def test_execution_sets_execution_result(self):
        """Test that execution sets context execution_result."""
        answer_text = "This is the final answer with detailed information"
        tool = FinalAnswerTool(
            reasoning="Task completed",
            completed_steps=["Step 1"],
            answer=answer_text,
            status=AgentStatesEnum.COMPLETED,
        )
        context = ResearchContext()
        await tool(context)

        assert context.execution_result == answer_text

    @pytest.mark.asyncio
    async def test_execution_json_contains_all_fields(self):
        """Test that JSON output contains all expected fields."""
        tool = FinalAnswerTool(
            reasoning="Task completed successfully",
            completed_steps=["Step 1", "Step 2"],
            answer="Final answer",
            status=AgentStatesEnum.COMPLETED,
        )
        context = ResearchContext()
        result = await tool(context)
        data = json.loads(result)

        assert "reasoning" in data
        assert "completed_steps" in data
        assert "answer" in data
        assert "status" in data

    @pytest.mark.asyncio
    async def test_execution_json_values_match_input(self):
        """Test that JSON output values match input values."""
        tool = FinalAnswerTool(
            reasoning="Task completed successfully",
            completed_steps=["Step 1", "Step 2"],
            answer="Detailed final answer",
            status=AgentStatesEnum.COMPLETED,
        )
        context = ResearchContext()
        result = await tool(context)
        data = json.loads(result)

        assert data["reasoning"] == "Task completed successfully"
        assert data["completed_steps"] == ["Step 1", "Step 2"]
        assert data["answer"] == "Detailed final answer"
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_execution_json_is_indented(self):
        """Test that JSON output is indented (indent=2)."""
        tool = FinalAnswerTool(
            reasoning="Task completed",
            completed_steps=["Step 1"],
            answer="Final answer",
            status=AgentStatesEnum.COMPLETED,
        )
        context = ResearchContext()
        result = await tool(context)

        # Indented JSON should contain newlines
        assert "\n" in result
        # Should contain proper indentation
        assert "  " in result

    @pytest.mark.asyncio
    async def test_execution_with_long_answer(self):
        """Test execution with a long answer text."""
        long_answer = "This is a very detailed answer. " * 100
        tool = FinalAnswerTool(
            reasoning="Task completed",
            completed_steps=["Step 1"],
            answer=long_answer,
            status=AgentStatesEnum.COMPLETED,
        )
        context = ResearchContext()
        result = await tool(context)

        assert context.execution_result == long_answer
        data = json.loads(result)
        assert data["answer"] == long_answer

    @pytest.mark.asyncio
    async def test_execution_with_multiline_answer(self):
        """Test execution with multiline answer."""
        multiline_answer = "Line 1\nLine 2\nLine 3"
        tool = FinalAnswerTool(
            reasoning="Task completed",
            completed_steps=["Step 1"],
            answer=multiline_answer,
            status=AgentStatesEnum.COMPLETED,
        )
        context = ResearchContext()
        result = await tool(context)

        assert context.execution_result == multiline_answer
        data = json.loads(result)
        assert data["answer"] == multiline_answer

    @pytest.mark.asyncio
    async def test_execution_preserves_other_context_fields(self):
        """Test that execution only modifies state and execution_result."""
        tool = FinalAnswerTool(
            reasoning="Task completed",
            completed_steps=["Step 1"],
            answer="Final answer",
            status=AgentStatesEnum.COMPLETED,
        )
        context = ResearchContext()
        context.iteration = 5
        context.searches_used = 3

        await tool(context)

        # These should remain unchanged
        assert context.iteration == 5
        assert context.searches_used == 3


class TestFinalAnswerToolAttributes:
    """Test class attributes and properties of FinalAnswerTool."""

    def test_tool_name_attribute(self):
        """Test that tool_name is correctly set."""
        assert FinalAnswerTool.tool_name == "finalanswertool"

    def test_tool_name_is_lowercase(self):
        """Test that tool_name is lowercase."""
        assert FinalAnswerTool.tool_name.islower()

    def test_description_exists(self):
        """Test that description exists and is not empty."""
        assert FinalAnswerTool.description is not None
        assert len(FinalAnswerTool.description) > 0

    def test_description_is_string(self):
        """Test that description is a string."""
        assert isinstance(FinalAnswerTool.description, str)

    def test_tool_is_base_tool_subclass(self):
        """Test that FinalAnswerTool is a subclass of BaseTool."""
        from sgr_deep_research.core.base_tool import BaseTool

        assert issubclass(FinalAnswerTool, BaseTool)


class TestFinalAnswerToolEdgeCases:
    """Test edge cases and unusual scenarios."""

    def test_with_empty_string_reasoning(self):
        """Test that empty string reasoning is allowed."""
        tool = FinalAnswerTool(
            reasoning="",
            completed_steps=["Step 1"],
            answer="Final answer",
            status=AgentStatesEnum.COMPLETED,
        )
        assert tool.reasoning == ""

    def test_with_empty_string_answer(self):
        """Test that empty string answer is allowed."""
        tool = FinalAnswerTool(
            reasoning="Task completed",
            completed_steps=["Step 1"],
            answer="",
            status=AgentStatesEnum.COMPLETED,
        )
        assert tool.answer == ""

    def test_with_special_characters_in_answer(self):
        """Test that special characters in answer are handled correctly."""
        special_answer = "Answer with special chars: <>&\"'$%"
        tool = FinalAnswerTool(
            reasoning="Task completed",
            completed_steps=["Step 1"],
            answer=special_answer,
            status=AgentStatesEnum.COMPLETED,
        )
        assert tool.answer == special_answer

    @pytest.mark.asyncio
    async def test_execution_with_special_characters_returns_valid_json(self):
        """Test that execution with special characters returns valid JSON."""
        special_answer = "Answer with special chars: <>&\"'$%"
        tool = FinalAnswerTool(
            reasoning="Task completed",
            completed_steps=["Step 1"],
            answer=special_answer,
            status=AgentStatesEnum.COMPLETED,
        )
        context = ResearchContext()
        result = await tool(context)
        data = json.loads(result)

        assert data["answer"] == special_answer

    def test_with_unicode_characters(self):
        """Test that Unicode characters are handled correctly."""
        unicode_answer = "答案是 42. Ответ: 42. 回答: 42 🎉"
        tool = FinalAnswerTool(
            reasoning="Задача выполнена",
            completed_steps=["步骤 1"],
            answer=unicode_answer,
            status=AgentStatesEnum.COMPLETED,
        )
        assert tool.answer == unicode_answer

    @pytest.mark.asyncio
    async def test_execution_with_unicode_returns_valid_json(self):
        """Test that execution with Unicode returns valid JSON."""
        unicode_answer = "答案是 42"
        tool = FinalAnswerTool(
            reasoning="Task completed",
            completed_steps=["Step 1"],
            answer=unicode_answer,
            status=AgentStatesEnum.COMPLETED,
        )
        context = ResearchContext()
        result = await tool(context)
        data = json.loads(result)

        assert data["answer"] == unicode_answer

    @pytest.mark.asyncio
    async def test_multiple_executions_update_context_correctly(self):
        """Test that multiple executions correctly update context."""
        context = ResearchContext()

        # First execution
        tool1 = FinalAnswerTool(
            reasoning="First attempt",
            completed_steps=["Step 1"],
            answer="First answer",
            status=AgentStatesEnum.FAILED,
        )
        await tool1(context)
        assert context.state == AgentStatesEnum.FAILED
        assert context.execution_result == "First answer"

        # Second execution (overwriting)
        tool2 = FinalAnswerTool(
            reasoning="Second attempt",
            completed_steps=["Step 1", "Step 2"],
            answer="Second answer",
            status=AgentStatesEnum.COMPLETED,
        )
        await tool2(context)
        assert context.state == AgentStatesEnum.COMPLETED
        assert context.execution_result == "Second answer"

    def test_completed_steps_with_long_strings(self):
        """Test completed_steps with very long step descriptions."""
        long_step = "This is a very detailed step description. " * 20
        tool = FinalAnswerTool(
            reasoning="Task completed",
            completed_steps=[long_step],
            answer="Final answer",
            status=AgentStatesEnum.COMPLETED,
        )
        assert tool.completed_steps[0] == long_step
