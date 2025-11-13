"""Extended tests for AdaptPlanTool.

This module contains comprehensive tests for the AdaptPlanTool, covering
validation, execution, JSON output, and plan adaptation scenarios.
"""

import json

import pytest
from pydantic import ValidationError

from sgr_deep_research.core.models import ResearchContext
from sgr_deep_research.core.tools import AdaptPlanTool


class TestAdaptPlanToolValidation:
    """Test validation rules for AdaptPlanTool fields."""

    def test_plan_changes_min_length(self):
        """Test validation fails when plan_changes is empty."""
        with pytest.raises(ValidationError) as exc_info:
            AdaptPlanTool(
                reasoning="Need to adapt",
                original_goal="Original goal",
                new_goal="New goal",
                plan_changes=[],
                next_steps=["Step 1", "Step 2"],
            )
        assert "plan_changes" in str(exc_info.value)

    def test_plan_changes_max_length(self):
        """Test validation fails when plan_changes exceeds 3 items."""
        with pytest.raises(ValidationError) as exc_info:
            AdaptPlanTool(
                reasoning="Need to adapt",
                original_goal="Original goal",
                new_goal="New goal",
                plan_changes=["Change 1", "Change 2", "Change 3", "Change 4"],
                next_steps=["Step 1", "Step 2"],
            )
        assert "plan_changes" in str(exc_info.value)

    def test_plan_changes_boundary_values(self):
        """Test plan_changes with boundary values (1 and 3 items)."""
        # Test with 1 item (min boundary)
        tool1 = AdaptPlanTool(
            reasoning="Need to adapt",
            original_goal="Original goal",
            new_goal="New goal",
            plan_changes=["Change 1"],
            next_steps=["Step 1", "Step 2"],
        )
        assert len(tool1.plan_changes) == 1

        # Test with 3 items (max boundary)
        tool3 = AdaptPlanTool(
            reasoning="Need to adapt",
            original_goal="Original goal",
            new_goal="New goal",
            plan_changes=["Change 1", "Change 2", "Change 3"],
            next_steps=["Step 1", "Step 2"],
        )
        assert len(tool3.plan_changes) == 3

    def test_next_steps_min_length(self):
        """Test validation fails when next_steps has less than 2 items."""
        with pytest.raises(ValidationError) as exc_info:
            AdaptPlanTool(
                reasoning="Need to adapt",
                original_goal="Original goal",
                new_goal="New goal",
                plan_changes=["Change 1"],
                next_steps=["Step 1"],
            )
        assert "next_steps" in str(exc_info.value)

    def test_next_steps_max_length(self):
        """Test validation fails when next_steps exceeds 4 items."""
        with pytest.raises(ValidationError) as exc_info:
            AdaptPlanTool(
                reasoning="Need to adapt",
                original_goal="Original goal",
                new_goal="New goal",
                plan_changes=["Change 1"],
                next_steps=["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"],
            )
        assert "next_steps" in str(exc_info.value)

    def test_next_steps_boundary_values(self):
        """Test next_steps with boundary values (2 and 4 items)."""
        # Test with 2 items (min boundary)
        tool2 = AdaptPlanTool(
            reasoning="Need to adapt",
            original_goal="Original goal",
            new_goal="New goal",
            plan_changes=["Change 1"],
            next_steps=["Step 1", "Step 2"],
        )
        assert len(tool2.next_steps) == 2

        # Test with 4 items (max boundary)
        tool4 = AdaptPlanTool(
            reasoning="Need to adapt",
            original_goal="Original goal",
            new_goal="New goal",
            plan_changes=["Change 1"],
            next_steps=["Step 1", "Step 2", "Step 3", "Step 4"],
        )
        assert len(tool4.next_steps) == 4

    def test_required_fields(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            AdaptPlanTool()

    def test_reasoning_required(self):
        """Test that reasoning field is required."""
        with pytest.raises(ValidationError) as exc_info:
            AdaptPlanTool(
                original_goal="Original goal",
                new_goal="New goal",
                plan_changes=["Change 1"],
                next_steps=["Step 1", "Step 2"],
            )
        assert "reasoning" in str(exc_info.value)

    def test_original_goal_required(self):
        """Test that original_goal field is required."""
        with pytest.raises(ValidationError) as exc_info:
            AdaptPlanTool(
                reasoning="Need to adapt",
                new_goal="New goal",
                plan_changes=["Change 1"],
                next_steps=["Step 1", "Step 2"],
            )
        assert "original_goal" in str(exc_info.value)

    def test_new_goal_required(self):
        """Test that new_goal field is required."""
        with pytest.raises(ValidationError) as exc_info:
            AdaptPlanTool(
                reasoning="Need to adapt",
                original_goal="Original goal",
                plan_changes=["Change 1"],
                next_steps=["Step 1", "Step 2"],
            )
        assert "new_goal" in str(exc_info.value)


class TestAdaptPlanToolExecution:
    """Test execution behavior of AdaptPlanTool."""

    @pytest.mark.asyncio
    async def test_execution_returns_string(self):
        """Test that execution returns a string."""
        tool = AdaptPlanTool(
            reasoning="Plan needs adaptation",
            original_goal="Original goal",
            new_goal="Updated goal",
            plan_changes=["Change 1"],
            next_steps=["Step 1", "Step 2"],
        )
        context = ResearchContext()
        result = await tool(context)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_execution_returns_valid_json(self):
        """Test that execution returns valid JSON."""
        tool = AdaptPlanTool(
            reasoning="Plan needs adaptation",
            original_goal="Original goal",
            new_goal="Updated goal",
            plan_changes=["Change 1"],
            next_steps=["Step 1", "Step 2"],
        )
        context = ResearchContext()
        result = await tool(context)

        data = json.loads(result)
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_execution_excludes_reasoning(self):
        """Test that reasoning field is excluded from JSON output."""
        tool = AdaptPlanTool(
            reasoning="This should be excluded",
            original_goal="Original goal",
            new_goal="Updated goal",
            plan_changes=["Change 1"],
            next_steps=["Step 1", "Step 2"],
        )
        context = ResearchContext()
        result = await tool(context)
        data = json.loads(result)

        assert "reasoning" not in data

    @pytest.mark.asyncio
    async def test_execution_json_contains_expected_fields(self):
        """Test that JSON output contains expected fields (excluding
        reasoning)."""
        tool = AdaptPlanTool(
            reasoning="Plan needs adaptation",
            original_goal="Original goal",
            new_goal="Updated goal",
            plan_changes=["Change 1"],
            next_steps=["Step 1", "Step 2"],
        )
        context = ResearchContext()
        result = await tool(context)
        data = json.loads(result)

        assert "original_goal" in data
        assert "new_goal" in data
        assert "plan_changes" in data
        assert "next_steps" in data

    @pytest.mark.asyncio
    async def test_execution_json_values_match_input(self):
        """Test that JSON output values match input values."""
        tool = AdaptPlanTool(
            reasoning="Plan needs adaptation",
            original_goal="Research AI basics",
            new_goal="Focus on deep learning",
            plan_changes=["Narrow scope", "Add GPU requirements"],
            next_steps=["Study neural networks", "Explore transformers"],
        )
        context = ResearchContext()
        result = await tool(context)
        data = json.loads(result)

        assert data["original_goal"] == "Research AI basics"
        assert data["new_goal"] == "Focus on deep learning"
        assert data["plan_changes"] == ["Narrow scope", "Add GPU requirements"]
        assert data["next_steps"] == ["Study neural networks", "Explore transformers"]

    @pytest.mark.asyncio
    async def test_execution_json_is_indented(self):
        """Test that JSON output is indented (indent=2)."""
        tool = AdaptPlanTool(
            reasoning="Plan needs adaptation",
            original_goal="Original goal",
            new_goal="Updated goal",
            plan_changes=["Change 1"],
            next_steps=["Step 1", "Step 2"],
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
        tool = AdaptPlanTool(
            reasoning="Plan needs adaptation",
            original_goal="Original goal",
            new_goal="Updated goal",
            plan_changes=["Change 1"],
            next_steps=["Step 1", "Step 2"],
        )
        context = ResearchContext()
        original_state = context.state
        original_iteration = context.iteration

        await tool(context)

        assert context.state == original_state
        assert context.iteration == original_iteration


class TestAdaptPlanToolAttributes:
    """Test class attributes and properties of AdaptPlanTool."""

    def test_tool_name_attribute(self):
        """Test that tool_name is correctly set."""
        assert AdaptPlanTool.tool_name == "adaptplantool"

    def test_tool_name_is_lowercase(self):
        """Test that tool_name is lowercase."""
        assert AdaptPlanTool.tool_name.islower()

    def test_description_exists(self):
        """Test that description exists and is not empty."""
        assert AdaptPlanTool.description is not None
        assert len(AdaptPlanTool.description) > 0

    def test_description_is_string(self):
        """Test that description is a string."""
        assert isinstance(AdaptPlanTool.description, str)

    def test_tool_is_base_tool_subclass(self):
        """Test that AdaptPlanTool is a subclass of BaseTool."""
        from sgr_deep_research.core.base_tool import BaseTool

        assert issubclass(AdaptPlanTool, BaseTool)


class TestAdaptPlanToolEdgeCases:
    """Test edge cases and unusual scenarios."""

    def test_with_empty_string_fields(self):
        """Test that empty strings are allowed in some fields."""
        tool = AdaptPlanTool(
            reasoning="",
            original_goal="",
            new_goal="",
            plan_changes=[""],
            next_steps=["", ""],
        )
        assert tool.reasoning == ""
        assert tool.original_goal == ""

    def test_with_same_original_and_new_goal(self):
        """Test with identical original_goal and new_goal."""
        tool = AdaptPlanTool(
            reasoning="Refine approach",
            original_goal="Research AI",
            new_goal="Research AI",
            plan_changes=["Change methodology"],
            next_steps=["Step 1", "Step 2"],
        )
        assert tool.original_goal == tool.new_goal

    def test_with_long_goals(self):
        """Test with very long goal descriptions."""
        long_goal = "This is a very detailed goal description. " * 50
        tool = AdaptPlanTool(
            reasoning="Plan needs adaptation",
            original_goal=long_goal,
            new_goal=long_goal + " Plus more details.",
            plan_changes=["Change 1"],
            next_steps=["Step 1", "Step 2"],
        )
        assert len(tool.original_goal) > 1000

    def test_with_unicode_characters(self):
        """Test that Unicode characters are handled correctly."""
        tool = AdaptPlanTool(
            reasoning="Нужна адаптация",
            original_goal="原始目標",
            new_goal="新しい目標",
            plan_changes=["Изменение 1", "変更 2"],
            next_steps=["Шаг 1", "步骤 2"],
        )
        assert "原始" in tool.original_goal
        assert "新しい" in tool.new_goal

    @pytest.mark.asyncio
    async def test_execution_with_unicode_returns_valid_json(self):
        """Test that execution with Unicode characters returns valid JSON."""
        tool = AdaptPlanTool(
            reasoning="Нужна адаптация",
            original_goal="原始目標",
            new_goal="新しい目標",
            plan_changes=["Изменение 1"],
            next_steps=["Шаг 1", "步骤 2"],
        )
        context = ResearchContext()
        result = await tool(context)
        data = json.loads(result)

        assert data["original_goal"] == "原始目標"
        assert data["new_goal"] == "新しい目標"

    def test_with_special_characters(self):
        """Test that special characters are handled correctly."""
        tool = AdaptPlanTool(
            reasoning="Adapt with special chars: <>&\"'",
            original_goal="Goal with $100 budget",
            new_goal="Goal with $200 budget",
            plan_changes=["Increase budget by 100%"],
            next_steps=["Step 1: A&B", "Step 2: <test>"],
        )
        assert "$100" in tool.original_goal
        assert "$200" in tool.new_goal

    @pytest.mark.asyncio
    async def test_execution_with_special_characters_returns_valid_json(self):
        """Test that execution with special characters returns valid JSON."""
        tool = AdaptPlanTool(
            reasoning="Adapt needed",
            original_goal="Goal with $100 budget",
            new_goal="Goal with $200 budget",
            plan_changes=["Increase budget by 100%"],
            next_steps=["Step 1: A&B", "Step 2: <test>"],
        )
        context = ResearchContext()
        result = await tool(context)
        data = json.loads(result)

        assert "$100" in data["original_goal"]
        assert "$200" in data["new_goal"]

    @pytest.mark.asyncio
    async def test_multiple_executions_produce_same_output(self):
        """Test that multiple executions of the same tool produce the same
        output."""
        tool = AdaptPlanTool(
            reasoning="Plan needs adaptation",
            original_goal="Original goal",
            new_goal="Updated goal",
            plan_changes=["Change 1"],
            next_steps=["Step 1", "Step 2"],
        )
        context = ResearchContext()

        result1 = await tool(context)
        result2 = await tool(context)

        assert result1 == result2

    def test_plan_changes_vs_next_steps_independence(self):
        """Test that plan_changes and next_steps are independent."""
        tool = AdaptPlanTool(
            reasoning="Plan needs adaptation",
            original_goal="Original goal",
            new_goal="Updated goal",
            plan_changes=["Major change 1", "Major change 2", "Major change 3"],
            next_steps=["Simple step 1", "Simple step 2"],
        )
        # Different lengths are fine - they are independent fields
        assert len(tool.plan_changes) == 3
        assert len(tool.next_steps) == 2

    @pytest.mark.asyncio
    async def test_execution_with_multiline_fields(self):
        """Test execution with multiline text in fields."""
        tool = AdaptPlanTool(
            reasoning="Plan needs adaptation",
            original_goal="Original goal\nWith multiple lines",
            new_goal="Updated goal\nAlso with\nMultiple lines",
            plan_changes=["Change 1\nWith details"],
            next_steps=["Step 1\nWith substeps", "Step 2"],
        )
        context = ResearchContext()
        result = await tool(context)
        data = json.loads(result)

        assert "With multiple lines" in data["original_goal"]
        assert "Multiple lines" in data["new_goal"]
