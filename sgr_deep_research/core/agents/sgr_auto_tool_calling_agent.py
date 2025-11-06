from typing import Literal, Type
from warnings import warn

from openai import AsyncOpenAI

from sgr_deep_research.core.agent_definition import ExecutionConfig, LLMConfig, PromptsConfig
from sgr_deep_research.core.agents.sgr_tool_calling_agent import SGRToolCallingAgent
from sgr_deep_research.core.tools import BaseTool


class SGRAutoToolCallingAgent(SGRToolCallingAgent):
    """SGR Tool Calling Research Agent variation for benchmark with automatic
    tool selection."""

    name: str = "sgr_auto_tool_calling_agent"

    def __init__(
        self,
        task: str,
        openai_client: AsyncOpenAI,
        llm_config: LLMConfig,
        prompts_config: PromptsConfig,
        execution_config: ExecutionConfig,
        toolkit: list[Type[BaseTool]] | None = None,
    ):
        super().__init__(
            task=task,
            openai_client=openai_client,
            llm_config=llm_config,
            prompts_config=prompts_config,
            execution_config=execution_config,
            toolkit=toolkit,
        )
        self.tool_choice: Literal["auto"] = "auto"
        warn(
            "SGRAutoToolCallingAgent is deprecated and will be removed in the future. "
            "This agent shows lower efficiency and stability based on our benchmarks.",
            DeprecationWarning,
        )
