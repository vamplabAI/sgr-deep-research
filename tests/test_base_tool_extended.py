"""Extended tests for BaseTool.

This module contains comprehensive tests for the BaseTool base class,
covering initialization, subclassing, tool_name generation, and abstract
methods.
"""

import pytest
from pydantic import BaseModel

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.models import ResearchContext


class TestBaseToolInitialization:
    """Test BaseTool initialization and class variables."""

    def test_base_tool_has_tool_name_attribute(self):
        """Test that BaseTool has tool_name class variable."""
        assert hasattr(BaseTool, "tool_name")

    def test_base_tool_has_description_attribute(self):
        """Test that BaseTool has description class variable."""
        assert hasattr(BaseTool, "description")

    def test_base_tool_default_tool_name_is_none(self):
        """Test that BaseTool default tool_name is None."""
        assert BaseTool.tool_name is None

    def test_base_tool_default_description_is_none(self):
        """Test that BaseTool default description is None."""
        assert BaseTool.description is None

    def test_base_tool_is_pydantic_model(self):
        """Test that BaseTool is a Pydantic BaseModel."""
        assert issubclass(BaseTool, BaseModel)

    def test_base_tool_can_be_instantiated(self):
        """Test that BaseTool can be instantiated."""
        tool = BaseTool()
        assert isinstance(tool, BaseTool)


class TestBaseToolSubclassing:
    """Test BaseTool subclassing and __init_subclass__ behavior."""

    def test_subclass_auto_generates_tool_name(self):
        """Test that subclass auto-generates tool_name from class name."""

        class MyCustomTool(BaseTool):
            pass

        assert MyCustomTool.tool_name == "mycustomtool"

    def test_subclass_tool_name_is_lowercase(self):
        """Test that auto-generated tool_name is lowercase."""

        class AnotherTestTool(BaseTool):
            pass

        assert AnotherTestTool.tool_name == "anothertesttool"
        assert AnotherTestTool.tool_name.islower()

    def test_subclass_with_custom_tool_name(self):
        """Test that subclass can override tool_name."""

        class CustomNamedTool(BaseTool):
            tool_name = "my_custom_name"

        assert CustomNamedTool.tool_name == "my_custom_name"

    def test_subclass_with_custom_description(self):
        """Test that subclass can set custom description."""

        class DescribedTool(BaseTool):
            description = "This is a custom description"

        assert DescribedTool.description == "This is a custom description"

    def test_subclass_without_docstring_has_empty_description(self):
        """Test that subclass without docstring has empty description."""

        class NoDocstringTool(BaseTool):
            pass

        assert NoDocstringTool.description == ""

    def test_subclass_with_docstring_auto_sets_description(self):
        """Test that subclass docstring becomes description."""

        class DocstringTool(BaseTool):
            """This is a tool with a docstring."""

            pass

        assert DocstringTool.description == "This is a tool with a docstring."

    def test_subclass_custom_description_overrides_docstring(self):
        """Test that custom description overrides docstring."""

        class OverrideTool(BaseTool):
            """This is a docstring."""

            description = "Custom description"

        assert OverrideTool.description == "Custom description"

    def test_multiple_subclasses_have_independent_names(self):
        """Test that multiple subclasses have independent tool names."""

        class Tool1(BaseTool):
            pass

        class Tool2(BaseTool):
            pass

        assert Tool1.tool_name == "tool1"
        assert Tool2.tool_name == "tool2"
        assert Tool1.tool_name != Tool2.tool_name

    def test_subclass_with_numbers_in_name(self):
        """Test subclass with numbers in class name."""

        class Tool123Test(BaseTool):
            pass

        assert Tool123Test.tool_name == "tool123test"

    def test_subclass_with_underscores_in_name(self):
        """Test subclass with underscores in class name."""

        class Tool_With_Underscores(BaseTool):
            pass

        assert Tool_With_Underscores.tool_name == "tool_with_underscores"


class TestBaseToolCallMethod:
    """Test BaseTool __call__ method behavior."""

    @pytest.mark.asyncio
    async def test_base_tool_call_raises_not_implemented(self):
        """Test that calling base tool raises NotImplementedError."""
        tool = BaseTool()
        context = ResearchContext()

        with pytest.raises(NotImplementedError) as exc_info:
            await tool(context)

        assert "Execute method must be implemented by subclass" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_subclass_without_call_raises_not_implemented(self):
        """Test that subclass without __call__ implementation raises error."""

        class IncompleteTool(BaseTool):
            pass

        tool = IncompleteTool()
        context = ResearchContext()

        with pytest.raises(NotImplementedError):
            await tool(context)

    @pytest.mark.asyncio
    async def test_subclass_with_call_implementation(self):
        """Test that subclass with __call__ implementation works."""

        class CompleteTool(BaseTool):
            async def __call__(self, context: ResearchContext) -> str:
                return "Tool executed"

        tool = CompleteTool()
        context = ResearchContext()
        result = await tool(context)

        assert result == "Tool executed"

    @pytest.mark.asyncio
    async def test_call_method_is_async(self):
        """Test that __call__ method is async."""
        import asyncio

        class AsyncTool(BaseTool):
            async def __call__(self, context: ResearchContext) -> str:
                await asyncio.sleep(0.01)
                return "Async completed"

        tool = AsyncTool()
        context = ResearchContext()
        result = await tool(context)

        assert result == "Async completed"


class TestBaseToolWithPydanticFields:
    """Test BaseTool subclasses with Pydantic fields."""

    def test_subclass_with_fields(self):
        """Test that subclass can have Pydantic fields."""
        from pydantic import Field

        class FieldTool(BaseTool):
            name: str = Field(description="Tool name")
            value: int = Field(default=0, description="Tool value")

        tool = FieldTool(name="test")
        assert tool.name == "test"
        assert tool.value == 0

    def test_subclass_field_validation(self):
        """Test that Pydantic validation works in subclass."""
        from pydantic import Field, ValidationError

        class ValidatedTool(BaseTool):
            count: int = Field(ge=0, le=10)

        # Valid value
        tool = ValidatedTool(count=5)
        assert tool.count == 5

        # Invalid value
        with pytest.raises(ValidationError):
            ValidatedTool(count=15)

    def test_subclass_with_list_field(self):
        """Test subclass with list field."""
        from pydantic import Field

        class ListTool(BaseTool):
            items: list[str] = Field(min_length=1, max_length=3)

        tool = ListTool(items=["a", "b"])
        assert len(tool.items) == 2

    def test_subclass_model_dump(self):
        """Test that subclass model_dump works correctly."""
        from pydantic import Field

        class DumpTool(BaseTool):
            name: str
            value: int = Field(default=42)

        tool = DumpTool(name="test")
        data = tool.model_dump()

        assert isinstance(data, dict)
        assert data["name"] == "test"
        assert data["value"] == 42


class TestBaseToolInheritance:
    """Test BaseTool inheritance patterns."""

    def test_multi_level_inheritance(self):
        """Test multi-level inheritance with BaseTool."""

        class IntermediateTool(BaseTool):
            """Intermediate tool."""

            pass

        class FinalTool(IntermediateTool):
            """Final tool."""

            pass

        # Inherited tool_name from IntermediateTool (not auto-generated)
        assert FinalTool.tool_name == "intermediatetool"
        # Description is also inherited from IntermediateTool
        assert FinalTool.description == "Intermediate tool."

    def test_intermediate_class_without_override(self):
        """Test intermediate class without tool_name override."""

        class MiddleTool(BaseTool):
            pass

        class EndTool(MiddleTool):
            pass

        assert MiddleTool.tool_name == "middletool"
        # EndTool inherits tool_name from MiddleTool
        assert EndTool.tool_name == "middletool"

    def test_inheritance_with_custom_names(self):
        """Test inheritance with custom tool names."""

        class Parent(BaseTool):
            tool_name = "parent_tool"

        class Child(Parent):
            pass

        # Child inherits the custom tool_name from Parent
        assert Child.tool_name == "parent_tool"

    def test_multiple_inheritance_not_recommended_but_works(self):
        """Test that multiple inheritance works (though not recommended)."""

        class Mixin:
            def helper_method(self):
                return "helper"

        class MixedTool(BaseTool, Mixin):
            pass

        tool = MixedTool()
        assert tool.helper_method() == "helper"
        assert MixedTool.tool_name == "mixedtool"


class TestBaseToolEdgeCases:
    """Test edge cases and unusual scenarios."""

    def test_subclass_with_empty_name(self):
        """Test subclass with very short name."""

        class T(BaseTool):
            pass

        assert T.tool_name == "t"

    def test_subclass_with_very_long_name(self):
        """Test subclass with very long name."""

        class ThisIsAVeryLongToolNameForTestingPurposes(BaseTool):
            pass

        expected = "thisisaverylongtoolnamefortestingpurposes"
        assert ThisIsAVeryLongToolNameForTestingPurposes.tool_name == expected

    def test_subclass_name_with_consecutive_capitals(self):
        """Test subclass name with consecutive capital letters."""

        class HTTPTool(BaseTool):
            pass

        assert HTTPTool.tool_name == "httptool"

    def test_subclass_with_multiline_docstring(self):
        """Test subclass with multiline docstring."""

        class MultilineTool(BaseTool):
            """This is a multiline docstring.

            It has multiple paragraphs.
            """

            pass

        assert "multiline docstring" in MultilineTool.description

    def test_subclass_with_special_characters_in_docstring(self):
        """Test subclass with special characters in docstring."""

        class SpecialTool(BaseTool):
            """Tool with special chars: <>&"'"""

            pass

        assert "<>&" in SpecialTool.description

    @pytest.mark.asyncio
    async def test_call_with_none_context(self):
        """Test calling with None context (should raise error in base)."""
        tool = BaseTool()

        with pytest.raises(NotImplementedError):
            await tool(None)

    def test_instance_attributes_vs_class_attributes(self):
        """Test that tool_name and description are class attributes."""
        from pydantic import Field

        class AttributeTool(BaseTool):
            value: int = Field(default=0)

        tool1 = AttributeTool()
        tool2 = AttributeTool(value=5)

        # tool_name and description should be shared class attributes
        assert tool1.tool_name == tool2.tool_name
        assert tool1.description == tool2.description
        assert AttributeTool.tool_name == "attributetool"


class TestBaseToolCompatibility:
    """Test BaseTool compatibility with existing tools."""

    def test_compatibility_with_clarification_tool(self):
        """Test that ClarificationTool is compatible with BaseTool."""
        from sgr_deep_research.core.tools import ClarificationTool

        assert issubclass(ClarificationTool, BaseTool)
        assert ClarificationTool.tool_name == "clarificationtool"

    def test_compatibility_with_reasoning_tool(self):
        """Test that ReasoningTool is compatible with BaseTool."""
        from sgr_deep_research.core.tools import ReasoningTool

        assert issubclass(ReasoningTool, BaseTool)
        assert ReasoningTool.tool_name == "reasoningtool"

    def test_compatibility_with_final_answer_tool(self):
        """Test that FinalAnswerTool is compatible with BaseTool."""
        from sgr_deep_research.core.tools import FinalAnswerTool

        assert issubclass(FinalAnswerTool, BaseTool)
        assert FinalAnswerTool.tool_name == "finalanswertool"

    def test_compatibility_with_generate_plan_tool(self):
        """Test that GeneratePlanTool is compatible with BaseTool."""
        from sgr_deep_research.core.tools import GeneratePlanTool

        assert issubclass(GeneratePlanTool, BaseTool)
        assert GeneratePlanTool.tool_name == "generateplantool"

    def test_compatibility_with_adapt_plan_tool(self):
        """Test that AdaptPlanTool is compatible with BaseTool."""
        from sgr_deep_research.core.tools import AdaptPlanTool

        assert issubclass(AdaptPlanTool, BaseTool)
        assert AdaptPlanTool.tool_name == "adaptplantool"
