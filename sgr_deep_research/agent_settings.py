import logging
from functools import cache
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, Field, model_validator

from sgr_deep_research.settings import OpenAIConfig, PromptsConfig, get_config

logger = logging.getLogger(__name__)


class AgentConfig(BaseModel, extra="allow"):
    """Agent execution context configuration."""

    max_iterations: int = Field(default=20, gt=0, description="Maximum number of iterations")
    max_clarifications: int = Field(default=3, ge=0, description="Maximum number of clarifications")
    max_searches: int = Field(default=4, ge=0, description="Maximum number of searches")


class AgentDefinition(BaseModel):
    """Definition of a custom agent.

    Agents can override global settings by providing:
    - openai: dict with keys matching OpenAIConfig (api_key, base_url, model, etc.)
    - prompts: dict with keys matching PromptsConfig (system_prompt_file, etc.)
    - context: AgentContextConfig with execution limits
    - tools: list of tool names to include
    """

    name: str = Field(description="Unique agent name/ID")
    display_name: str | None = Field(default=None, description="Human-readable agent name")
    description: str | None = Field(default=None, description="Agent description")
    base_class: str = Field(default="BaseAgent", description="Base agent class name")
    openai: OpenAIConfig | None = Field(
        default=None, description="Agent-specific OpenAI config overrides (same keys as OpenAIConfig)"
    )
    prompts: PromptsConfig | None = Field(
        default=None, description="Agent-specific prompts config overrides (same keys as PromptsConfig)"
    )
    config: AgentConfig = Field(default=AgentConfig(), description="Agent execution context configuration")
    tools: list[str] = Field(default_factory=list, description="List of tool names to include")

    @model_validator(mode="before")
    def defaults_validator(cls, data):
        if "openai" not in data or data["openai"] is None:
            data["openai"] = get_config().openai.model_dump()
        if "prompts" not in data or data["prompts"] is None:
            data["prompts"] = get_config().prompts.model_dump()
        return data


class AgentsConfig(BaseModel):
    agents: list[AgentDefinition] = Field(default_factory=list, description="List of agent definitions")

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> Self:
        if not yaml_path.exists():
            raise FileNotFoundError(f"Agents configuration file not found: {yaml_path}")

        with open(yaml_path, "r", encoding="utf-8") as f:
            return cls(**yaml.safe_load(f))


@cache
def get_agents_config() -> AgentsConfig:
    return AgentsConfig.from_yaml(Path(get_config().agents_config_path))
