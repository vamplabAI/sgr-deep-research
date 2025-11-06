from __future__ import annotations

import logging
import operator
from abc import ABC
from functools import reduce
from typing import Annotated, Literal, Type, TypeVar

from pydantic import BaseModel, Field, create_model

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.tools.reasoning_tool import ReasoningTool

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseTool)


class NextStepToolStub(ReasoningTool, ABC):
    """SGR Core - Determines the next reasoning step with adaptive planning, choosing appropriate tool
    (!) Stub class for correct autocomplete. Use NextStepToolsBuilder"""

    function: T = Field(description="Select the appropriate tool for the next step")


class DiscriminantToolMixin(BaseModel):
    tool_name_discriminator: str = Field(..., description="Tool name discriminator")

    def model_dump(self, *args, **kwargs):
        # it could cause unexpected field issues if not excluded
        exclude = kwargs.pop("exclude", set())
        exclude = exclude.union({"tool_name_discriminator"})
        return super().model_dump(*args, exclude=exclude, **kwargs)


class NextStepToolsBuilder:
    """SGR Core - Builder for NextStepTool with a dynamic union tool function type on
    pydantic models level."""

    @classmethod
    def _create_discriminant_tool(cls, tool_class: Type[T]) -> Type[BaseModel]:
        """Create a discriminant version of tool with tool_name as an instance
        field."""

        return create_model(  # noqa
            f"D_{tool_class.__name__}",
            __base__=(tool_class, DiscriminantToolMixin),  # the order matters here
            tool_name_discriminator=(Literal[tool_class.tool_name], Field(..., description="Tool name discriminator")),
        )

    @classmethod
    def _create_tool_types_union(cls, tools_list: list[Type[T]]) -> Type:
        """Create discriminated union of tools."""
        if len(tools_list) == 1:
            return cls._create_discriminant_tool(tools_list[0])
        # SGR inference struggles with choosing the right schema otherwise
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
