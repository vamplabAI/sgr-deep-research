"""Extended tests for GeneratePlanTool.

This module contains comprehensive tests for the GeneratePlanTool,
covering validation, execution, JSON output, and field exclusion.
"""

import json

import pytest
from pydantic import ValidationError

from sgr_deep_research.core.models import ResearchContext
from sgr_deep_research.core.tools import GeneratePlanTool


class TestGeneratePlanToolValidation:
    """Test validation rules for GeneratePlanTool fields."""

    def test_planned_steps_min_length(self):
        """Test validation fails when planned_steps has less than 3 items."""
        with pytest.raises(ValidationError) as exc_info:
            GeneratePlanTool(
                reasoning="Need a plan",
                research_goal="Understand the topic",
                planned_steps=["Step 1", "Step 2"],
                search_strategies=["Strategy 1", "Strategy 2"],
            )
        assert "planned_steps" in str(exc_info.value)

    def test_planned_steps_max_length(self):
        """Test validation fails when planned_steps exceeds 4 items."""
        with pytest.raises(ValidationError) as exc_info:
            GeneratePlanTool(
                reasoning="Need a plan",
                research_goal="Understand the topic",
                planned_steps=["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"],
                search_strategies=["Strategy 1", "Strategy 2"],
            )
        assert "planned_steps" in str(exc_info.value)

    def test_planned_steps_boundary_values(self):
        """Test planned_steps with boundary values (3 and 4 items)."""
        # Test with 3 items (min boundary)
        tool3 = GeneratePlanTool(
            reasoning="Need a plan",
            research_goal="Understand the topic",
            planned_steps=["Step 1", "Step 2", "Step 3"],
            search_strategies=["Strategy 1", "Strategy 2"],
        )
        assert len(tool3.planned_steps) == 3

        # Test with 4 items (max boundary)
        tool4 = GeneratePlanTool(
            reasoning="Need a plan",
            research_goal="Understand the topic",
            planned_steps=["Step 1", "Step 2", "Step 3", "Step 4"],
            search_strategies=["Strategy 1", "Strategy 2"],
        )
        assert len(tool4.planned_steps) == 4

    def test_search_strategies_min_length(self):
        """Test validation fails when search_strategies has less than 2 items."""
        with pytest.raises(ValidationError) as exc_info:
            GeneratePlanTool(
                reasoning="Need a plan",
                research_goal="Understand the topic",
                planned_steps=["Step 1", "Step 2", "Step 3"],
                search_strategies=["Strategy 1"],
            )
        assert "search_strategies" in str(exc_info.value)

    def test_search_strategies_max_length(self):
        """Test validation fails when search_strategies exceeds 3 items."""
        with pytest.raises(ValidationError) as exc_info:
            GeneratePlanTool(
                reasoning="Need a plan",
                research_goal="Understand the topic",
                planned_steps=["Step 1", "Step 2", "Step 3"],
                search_strategies=["Strategy 1", "Strategy 2", "Strategy 3", "Strategy 4"],
            )
        assert "search_strategies" in str(exc_info.value)

    def test_search_strategies_boundary_values(self):
        """Test search_strategies with boundary values (2 and 3 items)."""
        # Test with 2 items (min boundary)
        tool2 = GeneratePlanTool(
            reasoning="Need a plan",
            research_goal="Understand the topic",
            planned_steps=["Step 1", "Step 2", "Step 3"],
            search_strategies=["Strategy 1", "Strategy 2"],
        )
        assert len(tool2.search_strategies) == 2

        # Test with 3 items (max boundary)
        tool3 = GeneratePlanTool(
            reasoning="Need a plan",
            research_goal="Understand the topic",
            planned_steps=["Step 1", "Step 2", "Step 3"],
            search_strategies=["Strategy 1", "Strategy 2", "Strategy 3"],
        )
        assert len(tool3.search_strategies) == 3

    def test_required_fields(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            GeneratePlanTool()

    def test_reasoning_required(self):
        """Test that reasoning field is required."""
        with pytest.raises(ValidationError) as exc_info:
            GeneratePlanTool(
                research_goal="Understand the topic",
                planned_steps=["Step 1", "Step 2", "Step 3"],
                search_strategies=["Strategy 1", "Strategy 2"],
            )
        assert "reasoning" in str(exc_info.value)

    def test_research_goal_required(self):
        """Test that research_goal field is required."""
        with pytest.raises(ValidationError) as exc_info:
            GeneratePlanTool(
                reasoning="Need a plan",
                planned_steps=["Step 1", "Step 2", "Step 3"],
                search_strategies=["Strategy 1", "Strategy 2"],
            )
        assert "research_goal" in str(exc_info.value)


class TestGeneratePlanToolExecution:
    """Test execution behavior of GeneratePlanTool."""

    @pytest.mark.asyncio
    async def test_execution_returns_string(self):
        """Test that execution returns a string."""
        tool = GeneratePlanTool(
            reasoning="Need to create a plan",
            research_goal="Understand AI",
            planned_steps=["Step 1", "Step 2", "Step 3"],
            search_strategies=["Strategy 1", "Strategy 2"],
        )
        context = ResearchContext()
        result = await tool(context)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_execution_returns_valid_json(self):
        """Test that execution returns valid JSON."""
        tool = GeneratePlanTool(
            reasoning="Need to create a plan",
            research_goal="Understand AI",
            planned_steps=["Step 1", "Step 2", "Step 3"],
            search_strategies=["Strategy 1", "Strategy 2"],
        )
        context = ResearchContext()
        result = await tool(context)
        
        data = json.loads(result)
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_execution_excludes_reasoning(self):
        """Test that reasoning field is excluded from JSON output."""
        tool = GeneratePlanTool(
            reasoning="This should be excluded",
            research_goal="Understand AI",
            planned_steps=["Step 1", "Step 2", "Step 3"],
            search_strategies=["Strategy 1", "Strategy 2"],
        )
        context = ResearchContext()
        result = await tool(context)
        data = json.loads(result)
        
        assert "reasoning" not in data

    @pytest.mark.asyncio
    async def test_execution_json_contains_expected_fields(self):
        """Test that JSON output contains expected fields (excluding reasoning)."""
        tool = GeneratePlanTool(
            reasoning="Need to create a plan",
            research_goal="Understand AI",
            planned_steps=["Step 1", "Step 2", "Step 3"],
            search_strategies=["Strategy 1", "Strategy 2"],
        )
        context = ResearchContext()
        result = await tool(context)
        data = json.loads(result)
        
        assert "research_goal" in data
        assert "planned_steps" in data
        assert "search_strategies" in data

    @pytest.mark.asyncio
    async def test_execution_json_values_match_input(self):
        """Test that JSON output values match input values."""
        tool = GeneratePlanTool(
            reasoning="Need to create a plan",
            research_goal="Understand machine learning",
            planned_steps=["Gather data", "Analyze patterns", "Draw conclusions"],
            search_strategies=["Academic papers", "Industry reports"],
        )
        context = ResearchContext()
        result = await tool(context)
        data = json.loads(result)
        
        assert data["research_goal"] == "Understand machine learning"
        assert data["planned_steps"] == ["Gather data", "Analyze patterns", "Draw conclusions"]
        assert data["search_strategies"] == ["Academic papers", "Industry reports"]

    @pytest.mark.asyncio
    async def test_execution_json_is_indented(self):
        """Test that JSON output is indented (indent=2)."""
        tool = GeneratePlanTool(
            reasoning="Need a plan",
            research_goal="Understand AI",
            planned_steps=["Step 1", "Step 2", "Step 3"],
            search_strategies=["Strategy 1", "Strategy 2"],
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
        tool = GeneratePlanTool(
            reasoning="Need a plan",
            research_goal="Understand AI",
            planned_steps=["Step 1", "Step 2", "Step 3"],
            search_strategies=["Strategy 1", "Strategy 2"],
        )
        context = ResearchContext()
        original_state = context.state
        original_iteration = context.iteration
        
        await tool(context)
        
        assert context.state == original_state
        assert context.iteration == original_iteration


class TestGeneratePlanToolAttributes:
    """Test class attributes and properties of GeneratePlanTool."""

    def test_tool_name_attribute(self):
        """Test that tool_name is correctly set."""
        assert GeneratePlanTool.tool_name == "generateplantool"

    def test_tool_name_is_lowercase(self):
        """Test that tool_name is lowercase."""
        assert GeneratePlanTool.tool_name.islower()

    def test_description_exists(self):
        """Test that description exists and is not empty."""
        assert GeneratePlanTool.description is not None
        assert len(GeneratePlanTool.description) > 0

    def test_description_is_string(self):
        """Test that description is a string."""
        assert isinstance(GeneratePlanTool.description, str)

    def test_tool_is_base_tool_subclass(self):
        """Test that GeneratePlanTool is a subclass of BaseTool."""
        from sgr_deep_research.core.base_tool import BaseTool
        assert issubclass(GeneratePlanTool, BaseTool)


class TestGeneratePlanToolEdgeCases:
    """Test edge cases and unusual scenarios."""

    def test_with_empty_string_fields(self):
        """Test that empty strings are allowed in fields."""
        tool = GeneratePlanTool(
            reasoning="",
            research_goal="",
            planned_steps=["", "", ""],
            search_strategies=["", ""],
        )
        assert tool.reasoning == ""
        assert tool.research_goal == ""

    def test_with_long_research_goal(self):
        """Test with a very long research goal."""
        long_goal = "This is a very detailed research goal. " * 50
        tool = GeneratePlanTool(
            reasoning="Need a plan",
            research_goal=long_goal,
            planned_steps=["Step 1", "Step 2", "Step 3"],
            search_strategies=["Strategy 1", "Strategy 2"],
        )
        assert tool.research_goal == long_goal

    def test_with_long_steps(self):
        """Test with very long step descriptions."""
        long_step = "This is a very detailed step description. " * 20
        tool = GeneratePlanTool(
            reasoning="Need a plan",
            research_goal="Understand AI",
            planned_steps=[long_step, long_step, long_step],
            search_strategies=["Strategy 1", "Strategy 2"],
        )
        assert tool.planned_steps[0] == long_step

    def test_with_unicode_characters(self):
        """Test that Unicode characters are handled correctly."""
        tool = GeneratePlanTool(
            reasoning="Нужен план",
            research_goal="理解人工智能",
            planned_steps=["Шаг 1", "步骤 2", "ステップ 3"],
            search_strategies=["Стратегия 1", "策略 2"],
        )
        assert "理解" in tool.research_goal
        assert "Шаг" in tool.planned_steps[0]

    @pytest.mark.asyncio
    async def test_execution_with_unicode_returns_valid_json(self):
        """Test that execution with Unicode characters returns valid JSON."""
        tool = GeneratePlanTool(
            reasoning="Нужен план",
            research_goal="理解人工智能",
            planned_steps=["Шаг 1", "步骤 2", "ステップ 3"],
            search_strategies=["Стратегия 1", "策略 2"],
        )
        context = ResearchContext()
        result = await tool(context)
        data = json.loads(result)
        
        assert "理解" in data["research_goal"]
        assert data["planned_steps"][0] == "Шаг 1"

    def test_with_special_characters(self):
        """Test that special characters are handled correctly."""
        tool = GeneratePlanTool(
            reasoning="Plan with special chars: <>&\"'",
            research_goal="Research goal with $100 budget",
            planned_steps=["Step 1: A&B", "Step 2: <test>", "Step 3: 50%"],
            search_strategies=["Strategy #1", "Strategy $2"],
        )
        assert "$100" in tool.research_goal
        assert "A&B" in tool.planned_steps[0]

    @pytest.mark.asyncio
    async def test_execution_with_special_characters_returns_valid_json(self):
        """Test that execution with special characters returns valid JSON."""
        tool = GeneratePlanTool(
            reasoning="Plan needed",
            research_goal="Research goal with $100 budget",
            planned_steps=["Step 1: A&B", "Step 2: <test>", "Step 3: 50%"],
            search_strategies=["Strategy #1", "Strategy $2"],
        )
        context = ResearchContext()
        result = await tool(context)
        data = json.loads(result)
        
        assert "$100" in data["research_goal"]
        assert "A&B" in data["planned_steps"][0]

    @pytest.mark.asyncio
    async def test_multiple_executions_produce_same_output(self):
        """Test that multiple executions of the same tool produce the same output."""
        tool = GeneratePlanTool(
            reasoning="Need a plan",
            research_goal="Understand AI",
            planned_steps=["Step 1", "Step 2", "Step 3"],
            search_strategies=["Strategy 1", "Strategy 2"],
        )
        context = ResearchContext()
        
        result1 = await tool(context)
        result2 = await tool(context)
        
        assert result1 == result2

