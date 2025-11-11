"""Extended tests for ClarificationTool.

This module contains comprehensive tests for the ClarificationTool,
covering edge cases, validation, context interaction, and output
formatting.
"""

import pytest
from pydantic import ValidationError

from sgr_deep_research.core.models import ResearchContext
from sgr_deep_research.core.tools import ClarificationTool


class TestClarificationToolValidation:
    """Test validation rules for ClarificationTool fields."""

    def test_unclear_terms_min_length(self):
        """Test validation fails when unclear_terms list is empty."""
        with pytest.raises(ValidationError) as exc_info:
            ClarificationTool(
                reasoning="Need clarification",
                unclear_terms=[],
                assumptions=["Assumption 1", "Assumption 2"],
                questions=["Q1?", "Q2?", "Q3?"],
            )
        assert "unclear_terms" in str(exc_info.value)

    def test_unclear_terms_max_length(self):
        """Test validation fails when unclear_terms exceeds max length of 3."""
        with pytest.raises(ValidationError) as exc_info:
            ClarificationTool(
                reasoning="Need clarification",
                unclear_terms=["Term 1", "Term 2", "Term 3", "Term 4"],
                assumptions=["Assumption 1", "Assumption 2"],
                questions=["Q1?", "Q2?", "Q3?"],
            )
        assert "unclear_terms" in str(exc_info.value)

    def test_unclear_terms_boundary_values(self):
        """Test unclear_terms with boundary values (1 and 3 items)."""
        # Test with 1 item (min boundary)
        tool1 = ClarificationTool(
            reasoning="Need clarification",
            unclear_terms=["Term 1"],
            assumptions=["Assumption 1", "Assumption 2"],
            questions=["Q1?", "Q2?", "Q3?"],
        )
        assert len(tool1.unclear_terms) == 1

        # Test with 3 items (max boundary)
        tool3 = ClarificationTool(
            reasoning="Need clarification",
            unclear_terms=["Term 1", "Term 2", "Term 3"],
            assumptions=["Assumption 1", "Assumption 2"],
            questions=["Q1?", "Q2?", "Q3?"],
        )
        assert len(tool3.unclear_terms) == 3

    def test_assumptions_min_length(self):
        """Test validation fails when assumptions list has less than 2
        items."""
        with pytest.raises(ValidationError) as exc_info:
            ClarificationTool(
                reasoning="Need clarification",
                unclear_terms=["Term 1"],
                assumptions=["Assumption 1"],
                questions=["Q1?", "Q2?", "Q3?"],
            )
        assert "assumptions" in str(exc_info.value)

    def test_assumptions_max_length(self):
        """Test validation fails when assumptions exceeds max length of 3."""
        with pytest.raises(ValidationError) as exc_info:
            ClarificationTool(
                reasoning="Need clarification",
                unclear_terms=["Term 1"],
                assumptions=["Assumption 1", "Assumption 2", "Assumption 3", "Assumption 4"],
                questions=["Q1?", "Q2?", "Q3?"],
            )
        assert "assumptions" in str(exc_info.value)

    def test_assumptions_boundary_values(self):
        """Test assumptions with boundary values (2 and 3 items)."""
        # Test with 2 items (min boundary)
        tool2 = ClarificationTool(
            reasoning="Need clarification",
            unclear_terms=["Term 1"],
            assumptions=["Assumption 1", "Assumption 2"],
            questions=["Q1?", "Q2?", "Q3?"],
        )
        assert len(tool2.assumptions) == 2

        # Test with 3 items (max boundary)
        tool3 = ClarificationTool(
            reasoning="Need clarification",
            unclear_terms=["Term 1"],
            assumptions=["Assumption 1", "Assumption 2", "Assumption 3"],
            questions=["Q1?", "Q2?", "Q3?"],
        )
        assert len(tool3.assumptions) == 3

    def test_questions_exact_length(self):
        """Test that questions must be exactly 3 items."""
        # Less than 3 - should fail
        with pytest.raises(ValidationError) as exc_info:
            ClarificationTool(
                reasoning="Need clarification",
                unclear_terms=["Term 1"],
                assumptions=["Assumption 1", "Assumption 2"],
                questions=["Q1?", "Q2?"],
            )
        assert "questions" in str(exc_info.value)

        # More than 3 - should fail
        with pytest.raises(ValidationError) as exc_info:
            ClarificationTool(
                reasoning="Need clarification",
                unclear_terms=["Term 1"],
                assumptions=["Assumption 1", "Assumption 2"],
                questions=["Q1?", "Q2?", "Q3?", "Q4?"],
            )
        assert "questions" in str(exc_info.value)

        # Exactly 3 - should pass
        tool = ClarificationTool(
            reasoning="Need clarification",
            unclear_terms=["Term 1"],
            assumptions=["Assumption 1", "Assumption 2"],
            questions=["Q1?", "Q2?", "Q3?"],
        )
        assert len(tool.questions) == 3

    def test_reasoning_max_length(self):
        """Test validation fails when reasoning exceeds max_length of 200."""
        long_reasoning = "A" * 201
        with pytest.raises(ValidationError) as exc_info:
            ClarificationTool(
                reasoning=long_reasoning,
                unclear_terms=["Term 1"],
                assumptions=["Assumption 1", "Assumption 2"],
                questions=["Q1?", "Q2?", "Q3?"],
            )
        assert "reasoning" in str(exc_info.value)

    def test_reasoning_boundary_length(self):
        """Test reasoning at boundary length of 200 characters."""
        reasoning_200 = "A" * 200
        tool = ClarificationTool(
            reasoning=reasoning_200,
            unclear_terms=["Term 1"],
            assumptions=["Assumption 1", "Assumption 2"],
            questions=["Q1?", "Q2?", "Q3?"],
        )
        assert len(tool.reasoning) == 200

    def test_empty_strings_in_lists(self):
        """Test that empty strings in lists are handled correctly."""
        # This should be allowed by Pydantic
        tool = ClarificationTool(
            reasoning="Need clarification",
            unclear_terms=[""],
            assumptions=["Assumption 1", ""],
            questions=["", "", ""],
        )
        assert tool.unclear_terms == [""]
        assert tool.assumptions == ["Assumption 1", ""]
        assert tool.questions == ["", "", ""]


class TestClarificationToolExecution:
    """Test execution behavior of ClarificationTool."""

    @pytest.mark.asyncio
    async def test_execution_returns_string(self):
        """Test that execution returns a string."""
        tool = ClarificationTool(
            reasoning="Need clarification",
            unclear_terms=["Term 1"],
            assumptions=["Assumption 1", "Assumption 2"],
            questions=["Q1?", "Q2?", "Q3?"],
        )
        context = ResearchContext()
        result = await tool(context)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_execution_contains_all_questions(self):
        """Test that execution result contains all three questions."""
        questions = ["Question 1?", "Question 2?", "Question 3?"]
        tool = ClarificationTool(
            reasoning="Need clarification",
            unclear_terms=["Term 1"],
            assumptions=["Assumption 1", "Assumption 2"],
            questions=questions,
        )
        context = ResearchContext()
        result = await tool(context)

        for question in questions:
            assert question in result

    @pytest.mark.asyncio
    async def test_execution_questions_separated_by_newline(self):
        """Test that questions are separated by newlines."""
        tool = ClarificationTool(
            reasoning="Need clarification",
            unclear_terms=["Term 1"],
            assumptions=["Assumption 1", "Assumption 2"],
            questions=["Q1?", "Q2?", "Q3?"],
        )
        context = ResearchContext()
        result = await tool(context)

        assert result == "Q1?\nQ2?\nQ3?"

    @pytest.mark.asyncio
    async def test_execution_with_multiline_questions(self):
        """Test execution with multiline questions."""
        questions = [
            "What is the primary objective?\nPlease be specific.",
            "How should we approach this?",
            "When is the deadline?",
        ]
        tool = ClarificationTool(
            reasoning="Need clarification",
            unclear_terms=["Term 1"],
            assumptions=["Assumption 1", "Assumption 2"],
            questions=questions,
        )
        context = ResearchContext()
        result = await tool(context)

        assert questions[0] in result
        assert questions[1] in result
        assert questions[2] in result

    @pytest.mark.asyncio
    async def test_execution_does_not_modify_context(self):
        """Test that execution does not modify the context."""
        tool = ClarificationTool(
            reasoning="Need clarification",
            unclear_terms=["Term 1"],
            assumptions=["Assumption 1", "Assumption 2"],
            questions=["Q1?", "Q2?", "Q3?"],
        )
        context = ResearchContext()
        original_state = context.state
        original_iteration = context.iteration

        await tool(context)

        assert context.state == original_state
        assert context.iteration == original_iteration

    @pytest.mark.asyncio
    async def test_execution_with_special_characters(self):
        """Test execution with special characters in questions."""
        questions = ["What's the cost ($)?", "Is it 50% complete?", "Can we use <tags>?"]
        tool = ClarificationTool(
            reasoning="Need clarification",
            unclear_terms=["Term 1"],
            assumptions=["Assumption 1", "Assumption 2"],
            questions=questions,
        )
        context = ResearchContext()
        result = await tool(context)

        for question in questions:
            assert question in result


class TestClarificationToolAttributes:
    """Test class attributes and properties of ClarificationTool."""

    def test_tool_name_attribute(self):
        """Test that tool_name is correctly set."""
        assert ClarificationTool.tool_name == "clarificationtool"

    def test_tool_name_is_lowercase(self):
        """Test that tool_name is lowercase."""
        assert ClarificationTool.tool_name.islower()

    def test_description_exists(self):
        """Test that description exists and is not empty."""
        assert ClarificationTool.description is not None
        assert len(ClarificationTool.description) > 0

    def test_description_is_string(self):
        """Test that description is a string."""
        assert isinstance(ClarificationTool.description, str)

    def test_tool_is_base_tool_subclass(self):
        """Test that ClarificationTool is a subclass of BaseTool."""
        from sgr_deep_research.core.base_tool import BaseTool

        assert issubclass(ClarificationTool, BaseTool)

    def test_tool_instance_fields(self):
        """Test that tool instance has all required fields."""
        tool = ClarificationTool(
            reasoning="Need clarification",
            unclear_terms=["Term 1"],
            assumptions=["Assumption 1", "Assumption 2"],
            questions=["Q1?", "Q2?", "Q3?"],
        )
        assert hasattr(tool, "reasoning")
        assert hasattr(tool, "unclear_terms")
        assert hasattr(tool, "assumptions")
        assert hasattr(tool, "questions")


class TestClarificationToolSerialization:
    """Test serialization and deserialization of ClarificationTool."""

    def test_model_dump(self):
        """Test that model_dump returns a dictionary."""
        tool = ClarificationTool(
            reasoning="Need clarification",
            unclear_terms=["Term 1"],
            assumptions=["Assumption 1", "Assumption 2"],
            questions=["Q1?", "Q2?", "Q3?"],
        )
        data = tool.model_dump()

        assert isinstance(data, dict)
        assert data["reasoning"] == "Need clarification"
        assert data["unclear_terms"] == ["Term 1"]
        assert len(data["assumptions"]) == 2
        assert len(data["questions"]) == 3

    def test_model_dump_json(self):
        """Test that model_dump_json returns valid JSON."""
        tool = ClarificationTool(
            reasoning="Need clarification",
            unclear_terms=["Term 1"],
            assumptions=["Assumption 1", "Assumption 2"],
            questions=["Q1?", "Q2?", "Q3?"],
        )
        json_str = tool.model_dump_json()

        assert isinstance(json_str, str)
        import json

        data = json.loads(json_str)
        assert data["reasoning"] == "Need clarification"

    def test_model_validate(self):
        """Test that model can be reconstructed from dictionary."""
        data = {
            "reasoning": "Need clarification",
            "unclear_terms": ["Term 1"],
            "assumptions": ["Assumption 1", "Assumption 2"],
            "questions": ["Q1?", "Q2?", "Q3?"],
        }
        tool = ClarificationTool.model_validate(data)

        assert tool.reasoning == data["reasoning"]
        assert tool.unclear_terms == data["unclear_terms"]
        assert tool.assumptions == data["assumptions"]
        assert tool.questions == data["questions"]
