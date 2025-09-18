"""Tools registry system for automatic tool registration and categorization."""

from __future__ import annotations

from typing import Type

from sgr_deep_research.core.base_tool import BaseTool


class ToolsRegistry:
    """Registry for automatic tool registration and categorization."""

    _tools: dict[str, Type[BaseTool]] = {}

    @classmethod
    def register(cls, tool_class: Type[BaseTool]) -> None:
        """Register a tool class in the registry.

        Args:
            tool_class: Tool class that inherits from BaseTool
        """
        tool_name = tool_class.tool_name or tool_class.__name__
        cls._tools[tool_name] = tool_class

    @classmethod
    def get_tools(cls) -> list[Type[BaseTool]]:
        """Get all enabled tools (is_enabled = True).

        Returns:
            List of system tool classes
        """
        return [tool for tool in cls._tools.values() if tool.is_enabled]

    @classmethod
    def get_tool(cls, name: str) -> Type[BaseTool] | None:
        """Get a single tool by its name.

        Args:
            name: Tool name

        Returns:
            Tool class or None if not found
        """
        return cls._tools.get(name)

    @classmethod
    def disable_tool(cls, name: str) -> Type[BaseTool] | None:
        """Disable tool by its name.

        Args:
            name: Tool name

        Returns:
            Tool class or None if not found
        """
        cls._tools[name].is_enabled = False

    @classmethod
    def clear(cls) -> None:
        """Clear all registered tools (mainly for testing)."""
        cls._tools.clear()

    @classmethod
    def list_tools(cls) -> dict[str, dict[str, any]]:
        """Get detailed information about all registered tools.

        Returns:
            Dictionary with tool information
        """
        return {
            name: {
                "class": tool.__name__,
                "is_enabled": tool.is_enabled,
                "description": tool.description,
            }
            for name, tool in cls._tools.items()
        }


def tool(cls: Type[BaseTool]) -> Type[BaseTool]:
    """Decorator for automatic tool registration.

    This decorator automatically registers any class that inherits from BaseTool
    in the ToolsRegistry when the class is defined.

    Args:
        cls: Tool class that inherits from BaseTool

    Returns:
        The same class, but registered in the tools registry

    Example:
        @tool
        class MyTool(BaseTool):
            def __call__(self, context):
                return "result"
    """
    if not issubclass(cls, BaseTool):
        raise TypeError(
            f"@tool decorator can only be applied to classes that inherit from BaseTool, got {cls.__name__}"
        )

    ToolsRegistry.register(cls)
    return cls
