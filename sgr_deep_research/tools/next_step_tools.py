from __future__ import annotations

import operator
from abc import ABC
from functools import reduce
from typing import Type, TypeVar

from pydantic import Field, create_model

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.prompts import PromptLoader
from sgr_deep_research.tools.reasoning_tool import ReasoningTool

T = TypeVar("T", bound=BaseTool)


class NextStepToolStub(ReasoningTool, ABC):
    """SGR Core - Determines next reasoning step with adaptive planning, choosing appropriate tool.
    (!) Stub class for correct autocomplete. Use NextStepToolsBuilder.
    """

    function: BaseTool = Field(description=PromptLoader.get_tool_function_prompt())


class NextStepToolsBuilder:
    """SGR Core - Builder for NextStepTool with dynamic union tool function type on pydantic models level."""

    @classmethod
    def _create_tool_types_union(cls, tools_list: list[Type[BaseTool]]):
        if len(tools_list) == 1:
            return tools_list[0]

        return reduce(operator.or_, tools_list)

    @classmethod
    def build_NextStepTools(cls, tools_list: list[Type[BaseTool]]) -> Type[NextStepToolStub]:  # noqa
        tool_prompt = PromptLoader.get_tool_function_prompt()
        return create_model(
            "NextStepTools",
            __base__=NextStepToolStub,
            function=(cls._create_tool_types_union(tools_list), Field(description=tool_prompt)),
        )
