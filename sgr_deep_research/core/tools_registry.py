"""Tools registry system for automatic tool registration and categorization."""

from __future__ import annotations

from typing import Any, Type

from sgr_deep_research.core.base_tool import BaseTool


class ToolsRegistry:
    """Registry for automatic tool registration and categorization."""

    # Global registry of all available tools (populated by @tool decorator)
    _global_tools: dict[str, Type[BaseTool]] = {}

    def __init__(self):
        """Initialize instance registry with all available tools and their
        enabled status."""
        self._tools: dict[str, Type[BaseTool]] = self._global_tools.copy()
        self._disabled_tools: set[str] = set()

    @classmethod
    def register(cls, tool_class: Type[BaseTool]) -> None:
        """Register a tool class in the global registry.

        Args:
            tool_class: Tool class that inherits from BaseTool
        """
        tool_name = tool_class.tool_name or tool_class.__name__
        cls._global_tools[tool_name] = tool_class

    def get_tools(self) -> list[Type[BaseTool]]:
        """Get all enabled tools for this registry instance.

        Returns:
            List of enabled tool classes
        """
        return [tool for name, tool in self._tools.items() if tool.is_enabled and name not in self._disabled_tools]

    def get_tool(self, name: str) -> Type[BaseTool] | None:
        """Get a single tool by its name.

        Args:
            name: Tool name

        Returns:
            Tool class or None if not found
        """
        return self._tools.get(name)

    def disable_tool(self, name: str) -> bool:
        """Disable tool by its name for this registry instance.

        Args:
            name: Tool name

        Returns:
            True if tool was found and disabled, False otherwise
        """
        if name in self._tools:
            self._disabled_tools.add(name)
            return True
        return False

    def enable_tool(self, name: str) -> bool:
        """Enable tool by its name for this registry instance.

        Args:
            name: Tool name

        Returns:
            True if tool was found and enabled, False otherwise
        """
        if name in self._tools:
            self._disabled_tools.discard(name)
            return True
        return False

    def clear(self) -> None:
        """Clear all registered tools (mainly for testing)."""
        self._tools.clear()
        self._disabled_tools.clear()

    def list_tools(self) -> dict[str, dict[str, Any]]:
        """Get detailed information about all registered tools.

        Returns:
            Dictionary with tool information
        """
        return {
            name: {
                "class": tool.__name__,
                "is_enabled": tool.is_enabled and name not in self._disabled_tools,
                "description": tool.description,
            }
            for name, tool in self._tools.items()
        }

    @classmethod
    def get_default_registry(cls) -> "ToolsRegistry":
        """Get a new registry instance with all available tools."""
        return cls()


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
