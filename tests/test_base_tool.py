"""Tests for BaseTool base class.

This module contains tests for the BaseTool base class, covering
initialization, subclassing, and tool_name generation.
"""

from pydantic import BaseModel

from sgr_deep_research.core.base_tool import BaseTool


class TestBaseTool:
    """Test BaseTool base class functionality."""

    def test_base_tool_is_pydantic_model(self):
        """Test that BaseTool is a Pydantic BaseModel."""
        assert issubclass(BaseTool, BaseModel)

    def test_base_tool_can_be_instantiated(self):
        """Test that BaseTool can be instantiated."""
        tool = BaseTool()
        assert isinstance(tool, BaseTool)

    def test_base_tool_default_tool_name_is_none(self):
        """Test that BaseTool default tool_name is None."""
        assert BaseTool.tool_name is None

    def test_base_tool_default_description_is_none(self):
        """Test that BaseTool default description is None."""
        assert BaseTool.description is None

    def test_subclass_auto_generates_tool_name(self):
        """Test that subclass auto-generates tool_name from class name."""

        class MyCustomTool(BaseTool):
            pass

        assert MyCustomTool.tool_name == "mycustomtool"

    def test_subclass_preserves_custom_tool_name(self):
        """Test that subclass can override tool_name."""

        class MyCustomTool(BaseTool):
            tool_name = "custom_name"

        assert MyCustomTool.tool_name == "custom_name"

    def test_subclass_can_have_description(self):
        """Test that subclass can have description."""

        class MyCustomTool(BaseTool):
            description = "Custom tool description"

        assert MyCustomTool.description == "Custom tool description"
