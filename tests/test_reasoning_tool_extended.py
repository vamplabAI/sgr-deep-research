"""Extended tests for ReasoningTool.

This module contains comprehensive tests for the ReasoningTool, covering
validation, execution, JSON output, and context interaction.
"""

import json

import pytest
from pydantic import ValidationError

from sgr_deep_research.core.models import ResearchContext
from sgr_deep_research.core.tools import ReasoningTool


class TestReasoningToolValidation:
    """Test validation rules for ReasoningTool fields."""

    def test_reasoning_steps_min_length(self):
        """Test validation fails when reasoning_steps has less than 2 items."""
        with pytest.raises(ValidationError) as exc_info:
            ReasoningTool(
                reasoning_steps=["Step 1"],
                current_situation="Analyzing",
                plan_status="In progress",
                enough_data=True,
                remaining_steps=["Next step"],
                task_completed=False,
            )
        assert "reasoning_steps" in str(exc_info.value)

    def test_reasoning_steps_max_length(self):
        """Test validation fails when reasoning_steps exceeds 3 items."""
        with pytest.raises(ValidationError) as exc_info:
            ReasoningTool(
                reasoning_steps=["Step 1", "Step 2", "Step 3", "Step 4"],
                current_situation="Analyzing",
                plan_status="In progress",
                enough_data=True,
                remaining_steps=["Next step"],
                task_completed=False,
            )
        assert "reasoning_steps" in str(exc_info.value)

    def test_reasoning_steps_boundary_values(self):
        """Test reasoning_steps with boundary values (2 and 3 items)."""
        # Test with 2 items (min boundary)
        tool2 = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Analyzing",
            plan_status="In progress",
            enough_data=True,
            remaining_steps=["Next step"],
            task_completed=False,
        )
        assert len(tool2.reasoning_steps) == 2

        # Test with 3 items (max boundary)
        tool3 = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2", "Step 3"],
            current_situation="Analyzing",
            plan_status="In progress",
            enough_data=True,
            remaining_steps=["Next step"],
            task_completed=False,
        )
        assert len(tool3.reasoning_steps) == 3

    def test_current_situation_max_length(self):
        """Test validation fails when current_situation exceeds 300
        characters."""
        long_situation = "A" * 301
        with pytest.raises(ValidationError) as exc_info:
            ReasoningTool(
                reasoning_steps=["Step 1", "Step 2"],
                current_situation=long_situation,
                plan_status="In progress",
                enough_data=True,
                remaining_steps=["Next step"],
                task_completed=False,
            )
        assert "current_situation" in str(exc_info.value)

    def test_current_situation_boundary_length(self):
        """Test current_situation at boundary length of 300 characters."""
        situation_300 = "A" * 300
        tool = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation=situation_300,
            plan_status="In progress",
            enough_data=True,
            remaining_steps=["Next step"],
            task_completed=False,
        )
        assert len(tool.current_situation) == 300

    def test_plan_status_max_length(self):
        """Test validation fails when plan_status exceeds 150 characters."""
        long_status = "A" * 151
        with pytest.raises(ValidationError) as exc_info:
            ReasoningTool(
                reasoning_steps=["Step 1", "Step 2"],
                current_situation="Analyzing",
                plan_status=long_status,
                enough_data=True,
                remaining_steps=["Next step"],
                task_completed=False,
            )
        assert "plan_status" in str(exc_info.value)

    def test_plan_status_boundary_length(self):
        """Test plan_status at boundary length of 150 characters."""
        status_150 = "A" * 150
        tool = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Analyzing",
            plan_status=status_150,
            enough_data=True,
            remaining_steps=["Next step"],
            task_completed=False,
        )
        assert len(tool.plan_status) == 150

    def test_remaining_steps_min_length(self):
        """Test validation fails when remaining_steps is empty."""
        with pytest.raises(ValidationError) as exc_info:
            ReasoningTool(
                reasoning_steps=["Step 1", "Step 2"],
                current_situation="Analyzing",
                plan_status="In progress",
                enough_data=True,
                remaining_steps=[],
                task_completed=False,
            )
        assert "remaining_steps" in str(exc_info.value)

    def test_remaining_steps_max_length(self):
        """Test validation fails when remaining_steps exceeds 3 items."""
        with pytest.raises(ValidationError) as exc_info:
            ReasoningTool(
                reasoning_steps=["Step 1", "Step 2"],
                current_situation="Analyzing",
                plan_status="In progress",
                enough_data=True,
                remaining_steps=["Step 1", "Step 2", "Step 3", "Step 4"],
                task_completed=False,
            )
        assert "remaining_steps" in str(exc_info.value)

    def test_remaining_steps_boundary_values(self):
        """Test remaining_steps with boundary values (1 and 3 items)."""
        # Test with 1 item (min boundary)
        tool1 = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Analyzing",
            plan_status="In progress",
            enough_data=True,
            remaining_steps=["Step 1"],
            task_completed=False,
        )
        assert len(tool1.remaining_steps) == 1

        # Test with 3 items (max boundary)
        tool3 = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Analyzing",
            plan_status="In progress",
            enough_data=True,
            remaining_steps=["Step 1", "Step 2", "Step 3"],
            task_completed=False,
        )
        assert len(tool3.remaining_steps) == 3

    def test_enough_data_boolean(self):
        """Test that enough_data accepts boolean values."""
        tool_true = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Analyzing",
            plan_status="In progress",
            enough_data=True,
            remaining_steps=["Next step"],
            task_completed=False,
        )
        assert tool_true.enough_data is True

        tool_false = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Analyzing",
            plan_status="In progress",
            enough_data=False,
            remaining_steps=["Next step"],
            task_completed=False,
        )
        assert tool_false.enough_data is False

    def test_enough_data_default_value(self):
        """Test that enough_data has default value of False."""
        # Check field default using Pydantic model fields
        field_info = ReasoningTool.model_fields["enough_data"]
        assert field_info.default is False

    def test_task_completed_boolean(self):
        """Test that task_completed accepts boolean values."""
        tool_true = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Analyzing",
            plan_status="In progress",
            enough_data=True,
            remaining_steps=["Next step"],
            task_completed=True,
        )
        assert tool_true.task_completed is True

        tool_false = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Analyzing",
            plan_status="In progress",
            enough_data=True,
            remaining_steps=["Next step"],
            task_completed=False,
        )
        assert tool_false.task_completed is False


class TestReasoningToolExecution:
    """Test execution behavior of ReasoningTool."""

    @pytest.mark.asyncio
    async def test_execution_returns_string(self):
        """Test that execution returns a string."""
        tool = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Analyzing",
            plan_status="In progress",
            enough_data=True,
            remaining_steps=["Next step"],
            task_completed=False,
        )
        context = ResearchContext()
        result = await tool(context)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_execution_returns_valid_json(self):
        """Test that execution returns valid JSON."""
        tool = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Analyzing",
            plan_status="In progress",
            enough_data=True,
            remaining_steps=["Next step"],
            task_completed=False,
        )
        context = ResearchContext()
        result = await tool(context)

        # Should be parseable as JSON
        data = json.loads(result)
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_execution_json_contains_all_fields(self):
        """Test that JSON output contains all expected fields."""
        tool = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Analyzing data",
            plan_status="In progress",
            enough_data=True,
            remaining_steps=["Next step"],
            task_completed=False,
        )
        context = ResearchContext()
        result = await tool(context)
        data = json.loads(result)

        assert "reasoning_steps" in data
        assert "current_situation" in data
        assert "plan_status" in data
        assert "enough_data" in data
        assert "remaining_steps" in data
        assert "task_completed" in data

    @pytest.mark.asyncio
    async def test_execution_json_values_match_input(self):
        """Test that JSON output values match input values."""
        tool = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Analyzing data",
            plan_status="Almost done",
            enough_data=True,
            remaining_steps=["Final step"],
            task_completed=False,
        )
        context = ResearchContext()
        result = await tool(context)
        data = json.loads(result)

        assert data["reasoning_steps"] == ["Step 1", "Step 2"]
        assert data["current_situation"] == "Analyzing data"
        assert data["plan_status"] == "Almost done"
        assert data["enough_data"] is True
        assert data["remaining_steps"] == ["Final step"]
        assert data["task_completed"] is False

    @pytest.mark.asyncio
    async def test_execution_json_is_indented(self):
        """Test that JSON output is indented (indent=2)."""
        tool = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Analyzing",
            plan_status="In progress",
            enough_data=True,
            remaining_steps=["Next step"],
            task_completed=False,
        )
        context = ResearchContext()
        result = await tool(context)

        # Indented JSON should contain newlines
        assert "\n" in result
        # Should contain proper indentation
        assert "  " in result

    @pytest.mark.asyncio
    async def test_execution_does_not_modify_context(self):
        """Test that execution does not modify the context."""
        tool = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Analyzing",
            plan_status="In progress",
            enough_data=True,
            remaining_steps=["Next step"],
            task_completed=False,
        )
        context = ResearchContext()
        original_state = context.state
        original_iteration = context.iteration

        await tool(context)

        assert context.state == original_state
        assert context.iteration == original_iteration

    @pytest.mark.asyncio
    async def test_execution_with_special_characters(self):
        """Test execution with special characters in fields."""
        tool = ReasoningTool(
            reasoning_steps=["Step 1: analyze <data>", "Step 2: verify & test"],
            current_situation="Analyzing data with special chars: $, %, &",
            plan_status="50% complete",
            enough_data=True,
            remaining_steps=["Final step: report"],
            task_completed=False,
        )
        context = ResearchContext()
        result = await tool(context)
        data = json.loads(result)

        assert "$" in data["current_situation"]
        assert "&" in data["reasoning_steps"][1]


class TestReasoningToolAttributes:
    """Test class attributes and properties of ReasoningTool."""

    def test_tool_name_attribute(self):
        """Test that tool_name is correctly set."""
        assert ReasoningTool.tool_name == "reasoningtool"

    def test_tool_name_is_lowercase(self):
        """Test that tool_name is lowercase."""
        assert ReasoningTool.tool_name.islower()

    def test_description_exists(self):
        """Test that description exists and is not empty."""
        assert ReasoningTool.description is not None
        assert len(ReasoningTool.description) > 0

    def test_description_is_string(self):
        """Test that description is a string."""
        assert isinstance(ReasoningTool.description, str)

    def test_tool_is_base_tool_subclass(self):
        """Test that ReasoningTool is a subclass of BaseTool."""
        from sgr_deep_research.core.base_tool import BaseTool

        assert issubclass(ReasoningTool, BaseTool)


class TestReasoningToolEdgeCases:
    """Test edge cases and unusual scenarios."""

    def test_with_empty_string_fields(self):
        """Test that empty strings are allowed in some fields."""
        tool = ReasoningTool(
            reasoning_steps=["", "Step 2"],
            current_situation="",
            plan_status="",
            enough_data=False,
            remaining_steps=[""],
            task_completed=False,
        )
        assert tool.reasoning_steps[0] == ""
        assert tool.current_situation == ""
        assert tool.plan_status == ""

    def test_with_unicode_characters(self):
        """Test that Unicode characters are handled correctly."""
        tool = ReasoningTool(
            reasoning_steps=["Шаг 1", "步骤 2"],
            current_situation="分析中 🔍",
            plan_status="В процессе 🚀",
            enough_data=False,
            remaining_steps=["次のステップ"],
            task_completed=False,
        )
        assert tool.reasoning_steps[0] == "Шаг 1"
        assert "🔍" in tool.current_situation

    @pytest.mark.asyncio
    async def test_execution_with_unicode_returns_valid_json(self):
        """Test that execution with Unicode characters returns valid JSON."""
        tool = ReasoningTool(
            reasoning_steps=["Шаг 1", "步骤 2"],
            current_situation="分析中",
            plan_status="В процессе",
            enough_data=False,
            remaining_steps=["次のステップ"],
            task_completed=False,
        )
        context = ResearchContext()
        result = await tool(context)
        data = json.loads(result)

        assert data["reasoning_steps"][0] == "Шаг 1"
        assert data["current_situation"] == "分析中"

    def test_all_booleans_false(self):
        """Test with all boolean fields set to False."""
        tool = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Starting",
            plan_status="Just started",
            enough_data=False,
            remaining_steps=["Step 1", "Step 2", "Step 3"],
            task_completed=False,
        )
        assert tool.enough_data is False
        assert tool.task_completed is False

    def test_all_booleans_true(self):
        """Test with all boolean fields set to True."""
        tool = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Finishing",
            plan_status="Complete",
            enough_data=True,
            remaining_steps=["Final check"],
            task_completed=True,
        )
        assert tool.enough_data is True
        assert tool.task_completed is True
