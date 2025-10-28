"""Tests for core tools module.

This module contains tests for various tools used in the SGR Deep Research system.
"""

import pytest
from pydantic import ValidationError

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.models import AgentStatesEnum, ResearchContext
from sgr_deep_research.core.tools import (
    AdaptPlanTool,
    ClarificationTool,
    FinalAnswerTool,
    GeneratePlanTool,
    ReasoningTool,
)


class TestClarificationTool:
    """Tests for ClarificationTool."""

    def test_clarification_tool_creation(self):
        """Test creating a clarification tool with valid data."""
        tool = ClarificationTool(
            reasoning="Need to clarify the context",
            unclear_terms=["term1", "term2"],
            assumptions=["assumption1", "assumption2"],
            questions=["Question 1?", "Question 2?", "Question 3?"],
        )
        assert tool.reasoning == "Need to clarify the context"
        assert len(tool.unclear_terms) == 2
        assert len(tool.assumptions) == 2
        assert len(tool.questions) == 3

    def test_clarification_tool_name(self):
        """Test that tool has correct name."""
        assert ClarificationTool.tool_name == "clarificationtool"

    def test_clarification_tool_description(self):
        """Test that tool has a description."""
        assert ClarificationTool.description is not None
        assert len(ClarificationTool.description) > 0

    def test_clarification_tool_validation_too_many_unclear_terms(self):
        """Test validation fails with too many unclear terms."""
        with pytest.raises(ValidationError):
            ClarificationTool(
                reasoning="Need to clarify",
                unclear_terms=["term1", "term2", "term3", "term4"],
                assumptions=["assumption1", "assumption2"],
                questions=["Question 1?", "Question 2?", "Question 3?"],
            )

    def test_clarification_tool_validation_too_few_questions(self):
        """Test validation fails with too few questions."""
        with pytest.raises(ValidationError):
            ClarificationTool(
                reasoning="Need to clarify",
                unclear_terms=["term1"],
                assumptions=["assumption1", "assumption2"],
                questions=["Question 1?"],
            )

    @pytest.mark.asyncio
    async def test_clarification_tool_execution(self):
        """Test clarification tool execution returns questions."""
        tool = ClarificationTool(
            reasoning="Need to clarify",
            unclear_terms=["term1", "term2"],
            assumptions=["assumption1", "assumption2"],
            questions=["Question 1?", "Question 2?", "Question 3?"],
        )
        context = ResearchContext()
        result = await tool(context)
        assert "Question 1?" in result
        assert "Question 2?" in result
        assert "Question 3?" in result


class TestReasoningTool:
    """Tests for ReasoningTool."""

    def test_reasoning_tool_creation(self):
        """Test creating a reasoning tool with valid data."""
        tool = ReasoningTool(
            reasoning_steps=["Step 1", "Step 2"],
            current_situation="Analyzing data",
            plan_status="In progress",
            enough_data=True,
            remaining_steps=["Next step"],
            task_completed=False,
        )
        assert len(tool.reasoning_steps) == 2
        assert tool.current_situation == "Analyzing data"
        assert tool.enough_data is True
        assert tool.task_completed is False

    def test_reasoning_tool_name(self):
        """Test that tool has correct name."""
        assert ReasoningTool.tool_name == "reasoningtool"

    def test_reasoning_tool_description(self):
        """Test that tool has a description."""
        assert ReasoningTool.description is not None

    def test_reasoning_tool_validation_too_many_steps(self):
        """Test validation fails with too many reasoning steps."""
        with pytest.raises(ValidationError):
            ReasoningTool(
                reasoning_steps=["Step 1", "Step 2", "Step 3", "Step 4"],
                current_situation="Analyzing",
                plan_status="In progress",
                enough_data=True,
                remaining_steps=["Next step"],
                task_completed=False,
            )

    def test_reasoning_tool_validation_situation_too_long(self):
        """Test validation fails with too long situation description."""
        long_situation = "A" * 301  # Exceeds max_length=300
        with pytest.raises(ValidationError):
            ReasoningTool(
                reasoning_steps=["Step 1", "Step 2"],
                current_situation=long_situation,
                plan_status="In progress",
                enough_data=True,
                remaining_steps=["Next step"],
                task_completed=False,
            )

    @pytest.mark.asyncio
    async def test_reasoning_tool_execution(self):
        """Test reasoning tool execution returns JSON."""
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
        assert isinstance(result, str)
        assert "reasoning_steps" in result
        assert "current_situation" in result


class TestFinalAnswerTool:
    """Tests for FinalAnswerTool."""

    def test_final_answer_tool_creation(self):
        """Test creating a final answer tool with valid data."""
        tool = FinalAnswerTool(
            reasoning="Task completed successfully",
            completed_steps=["Step 1", "Step 2"],
            answer="The answer is 42",
            status=AgentStatesEnum.COMPLETED,
        )
        assert tool.reasoning == "Task completed successfully"
        assert len(tool.completed_steps) == 2
        assert tool.answer == "The answer is 42"
        assert tool.status == AgentStatesEnum.COMPLETED

    def test_final_answer_tool_name(self):
        """Test that tool has correct name."""
        assert FinalAnswerTool.tool_name == "finalanswertool"

    def test_final_answer_tool_description(self):
        """Test that tool has a description."""
        assert FinalAnswerTool.description is not None

    def test_final_answer_tool_validation_too_many_steps(self):
        """Test validation fails with too many completed steps."""
        with pytest.raises(ValidationError):
            FinalAnswerTool(
                reasoning="Completed",
                completed_steps=["Step 1", "Step 2", "Step 3", "Step 4", "Step 5", "Step 6"],
                answer="Answer",
                status=AgentStatesEnum.COMPLETED,
            )

    @pytest.mark.asyncio
    async def test_final_answer_tool_execution_sets_state(self):
        """Test final answer tool execution sets context state."""
        tool = FinalAnswerTool(
            reasoning="Completed",
            completed_steps=["Step 1"],
            answer="Final answer",
            status=AgentStatesEnum.COMPLETED,
        )
        context = ResearchContext()
        await tool(context)
        assert context.state == AgentStatesEnum.COMPLETED
        assert context.execution_result == "Final answer"

    @pytest.mark.asyncio
    async def test_final_answer_tool_execution_returns_json(self):
        """Test final answer tool execution returns JSON."""
        tool = FinalAnswerTool(
            reasoning="Completed",
            completed_steps=["Step 1"],
            answer="Final answer",
            status=AgentStatesEnum.COMPLETED,
        )
        context = ResearchContext()
        result = await tool(context)
        assert isinstance(result, str)
        assert "answer" in result
        assert "reasoning" in result


class TestGeneratePlanTool:
    """Tests for GeneratePlanTool."""

    def test_generate_plan_tool_creation(self):
        """Test creating a generate plan tool with valid data."""
        tool = GeneratePlanTool(
            reasoning="Need to create research plan",
            research_goal="Understand the topic",
            planned_steps=["Step 1", "Step 2", "Step 3"],
            search_strategies=["Strategy 1", "Strategy 2"],
        )
        assert tool.reasoning == "Need to create research plan"
        assert tool.research_goal == "Understand the topic"
        assert len(tool.planned_steps) == 3
        assert len(tool.search_strategies) == 2

    def test_generate_plan_tool_name(self):
        """Test that tool has correct name."""
        assert GeneratePlanTool.tool_name == "generateplantool"

    def test_generate_plan_tool_description(self):
        """Test that tool has a description."""
        assert GeneratePlanTool.description is not None

    def test_generate_plan_tool_validation_too_few_steps(self):
        """Test validation fails with too few planned steps."""
        with pytest.raises(ValidationError):
            GeneratePlanTool(
                reasoning="Need plan",
                research_goal="Goal",
                planned_steps=["Step 1"],
                search_strategies=["Strategy 1", "Strategy 2"],
            )

    def test_generate_plan_tool_validation_too_many_steps(self):
        """Test validation fails with too many planned steps."""
        with pytest.raises(ValidationError):
            GeneratePlanTool(
                reasoning="Need plan",
                research_goal="Goal",
                planned_steps=["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"],
                search_strategies=["Strategy 1", "Strategy 2"],
            )

    @pytest.mark.asyncio
    async def test_generate_plan_tool_execution(self):
        """Test generate plan tool execution returns JSON without reasoning."""
        tool = GeneratePlanTool(
            reasoning="Need to create research plan",
            research_goal="Understand the topic",
            planned_steps=["Step 1", "Step 2", "Step 3"],
            search_strategies=["Strategy 1", "Strategy 2"],
        )
        context = ResearchContext()
        result = await tool(context)
        assert isinstance(result, str)
        assert "research_goal" in result
        assert "planned_steps" in result
        assert "reasoning" not in result  # Should be excluded


class TestAdaptPlanTool:
    """Tests for AdaptPlanTool."""

    def test_adapt_plan_tool_creation(self):
        """Test creating an adapt plan tool with valid data."""
        tool = AdaptPlanTool(
            reasoning="Need to adapt plan",
            original_goal="Original goal",
            new_goal="New goal",
            plan_changes=["Change 1", "Change 2"],
            next_steps=["Step 1", "Step 2", "Step 3"],
        )
        assert tool.reasoning == "Need to adapt plan"
        assert tool.original_goal == "Original goal"
        assert tool.new_goal == "New goal"
        assert len(tool.plan_changes) == 2
        assert len(tool.next_steps) == 3

    def test_adapt_plan_tool_name(self):
        """Test that tool has correct name."""
        assert AdaptPlanTool.tool_name == "adaptplantool"

    def test_adapt_plan_tool_description(self):
        """Test that tool has a description."""
        assert AdaptPlanTool.description is not None

    def test_adapt_plan_tool_validation_no_plan_changes(self):
        """Test validation fails with empty plan changes."""
        with pytest.raises(ValidationError):
            AdaptPlanTool(
                reasoning="Need to adapt",
                original_goal="Original",
                new_goal="New",
                plan_changes=[],
                next_steps=["Step 1", "Step 2"],
            )

    def test_adapt_plan_tool_validation_too_many_changes(self):
        """Test validation fails with too many plan changes."""
        with pytest.raises(ValidationError):
            AdaptPlanTool(
                reasoning="Need to adapt",
                original_goal="Original",
                new_goal="New",
                plan_changes=["Change 1", "Change 2", "Change 3", "Change 4"],
                next_steps=["Step 1", "Step 2"],
            )

    @pytest.mark.asyncio
    async def test_adapt_plan_tool_execution(self):
        """Test adapt plan tool execution returns JSON without reasoning."""
        tool = AdaptPlanTool(
            reasoning="Need to adapt plan",
            original_goal="Original goal",
            new_goal="New goal",
            plan_changes=["Change 1"],
            next_steps=["Step 1", "Step 2"],
        )
        context = ResearchContext()
        result = await tool(context)
        assert isinstance(result, str)
        assert "original_goal" in result
        assert "new_goal" in result
        assert "plan_changes" in result
        assert "reasoning" not in result  # Should be excluded


class TestBaseTool:
    """Tests for BaseTool base class."""

    def test_base_tool_tool_name_attribute(self):
        """Test that BaseTool has tool_name class variable."""
        assert hasattr(BaseTool, "tool_name")

    def test_base_tool_description_attribute(self):
        """Test that BaseTool has description class variable."""
        assert hasattr(BaseTool, "description")

    def test_base_tool_init_subclass_sets_name(self):
        """Test that __init_subclass__ sets tool_name from class name."""
        # Test with a concrete tool
        assert ClarificationTool.tool_name == "clarificationtool"

    def test_custom_tool_name(self):
        """Test that a tool can have a custom tool_name."""
        # Create a simple test tool class
        class CustomTool(BaseTool):
            tool_name = "custom_name"

        assert CustomTool.tool_name == "custom_name"

    @pytest.mark.asyncio
    async def test_base_tool_not_implemented_error(self):
        """Test that calling base tool raises NotImplementedError."""
        tool = BaseTool()
        context = ResearchContext()
        with pytest.raises(NotImplementedError):
            await tool(context)

