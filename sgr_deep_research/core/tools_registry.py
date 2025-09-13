"""Tools registry system for automatic tool registration and categorization."""

from __future__ import annotations

from typing import Type, TypeVar

from sgr_deep_research.core.base_tool import BaseTool

T = TypeVar("T", bound=BaseTool)


class ToolsRegistry:
    """Registry for automatic tool registration and categorization."""
    
    _tools: dict[str, Type[BaseTool]] = {}
    
    @classmethod
    def register(cls, tool_class: Type[BaseTool]) -> None:
        """Register a tool class in the registry.
        
        Args:
            tool_class: Tool class that inherits from BaseTool
        """
        tool_name = tool_class.tool_name or tool_class.__name__.lower()
        cls._tools[tool_name] = tool_class
    
    @classmethod
    def get_all_tools(cls) -> list[Type[BaseTool]]:
        """Get all registered tools.
        
        Returns:
            List of all registered tool classes
        """
        return list(cls._tools.values())
    
    @classmethod
    def get_system_tools(cls) -> list[Type[BaseTool]]:
        """Get all system tools (is_system_tool = True).
        
        Returns:
            List of system tool classes
        """
        return [tool for tool in cls._tools.values() if tool.is_system_tool]
    
    @classmethod
    def get_research_tools(cls) -> list[Type[BaseTool]]:
        """Get all research tools (is_system_tool = False).
        
        Returns:
            List of research tool classes
        """
        return [tool for tool in cls._tools.values() if not tool.is_system_tool]
    
    @classmethod
    def get_tool_by_name(cls, name: str) -> Type[BaseTool] | None:
        """Get a tool by its name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool class or None if not found
        """
        return cls._tools.get(name)
    
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
                "is_system_tool": tool.is_system_tool,
                "description": tool.description,
            }
            for name, tool in cls._tools.items()
        }


def tool(cls: Type[T]) -> Type[T]:
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


# Convenience aliases for backward compatibility
system_agent_tools = ToolsRegistry.get_system_tools
research_agent_tools = ToolsRegistry.get_research_tools
