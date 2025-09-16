from __future__ import annotations

import operator
from abc import ABC
from functools import reduce
from typing import Annotated, Type, Literal

from pydantic import BaseModel, Field, create_model

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.tools.reasoning_tool import ReasoningTool


class NextStepToolStub(ReasoningTool, ABC):
    """SGR Core - Determines next reasoning step with adaptive planning, choosing appropriate tool
    (!) Stub class for correct autocomplete. Use NextStepToolsBuilder"""

    function: BaseTool = Field(description="Select the appropriate tool for the next step")


class NextStepToolsBuilder:
    """SGR Core - Builder for NextStepTool with dynamic union tool function type on
    pydantic models level."""

    @classmethod
    def _create_discriminant_tool(cls, tool_class: Type[BaseTool]) -> Type[BaseModel]:
        """Create discriminant version of tool with tool_name as instance
        field."""
        tool_name = tool_class.tool_name

        discriminant_tool = create_model(
            f"{tool_class.__name__}WithDiscriminant",
            __base__=tool_class,
            tool_name_discriminator=(
                Literal[tool_name],  # noqa
                Field(default=tool_name, description="Tool name discriminator"),
            ),
        )
        discriminant_tool.__call__ = tool_class.__call__

        return discriminant_tool

    @classmethod
    def _create_tool_types_union(cls, tools_list: list[Type[BaseTool]]) -> Type:
        """Create discriminated union of tools."""
        if len(tools_list) == 1:
            return cls._create_discriminant_tool(tools_list[0])
        # SGR inference struggles with choosing right schema otherwise
        discriminant_tools = [cls._create_discriminant_tool(tool) for tool in tools_list]
        union = reduce(operator.or_, discriminant_tools)
        return Annotated[union, Field()]

    @classmethod
    def build_NextStepTools(cls, tools_list: list[Type[T]]) -> Type[NextStepToolStub]:  # noqa
        return create_model(
            "NextStepTools",
            __base__=NextStepToolStub,
            function=(cls._create_tool_types_union(tools_list), Field()),
        )
