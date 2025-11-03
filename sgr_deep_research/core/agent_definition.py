import logging
from functools import cache
from pathlib import Path
from typing import Self

import yaml
from fastmcp.client.transports import MCPConfigTransport
from fastmcp.mcp_config import MCPConfig
from pydantic import BaseModel, ConfigDict, Field, model_validator

from sgr_deep_research.core.base_agent import BaseAgent
from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.settings import LLMConfig, PromptsConfig, get_config

logger = logging.getLogger(__name__)


class AgentConfig(BaseModel, extra="allow"):
    """Agent execution context configuration."""

    max_iterations: int = Field(default=20, gt=0, description="Maximum number of iterations")
    max_clarifications: int = Field(default=3, ge=0, description="Maximum number of clarifications")
    max_searches: int = Field(default=4, ge=0, description="Maximum number of searches")


class MCPServerConfig(BaseModel):
    """Configuration for MCP server connection."""

    name: str = Field(description="MCP server name/ID")
    url: str = Field(description="MCP server URL")
    transport: MCPConfigTransport

    model_config = ConfigDict(arbitrary_types_allowed=True)


class AgentDefinition(BaseModel):
    """Definition of a custom agent.

    Agents can override global settings by providing:
    - openai: dict with keys matching LLMConfig (api_key, base_url, model, etc.)
    - prompts: dict with keys matching PromptsConfig (system_prompt_file, etc.)
    - context: AgentContextConfig with execution limits
    - tools: list of tool names to include
    """

    name: str = Field(description="Unique agent name/ID")
    base_class: type[BaseAgent] | str = Field(description="Agent class name")
    openai: LLMConfig | None = Field(
        default=None, description="Agent-specific LLM config overrides (same keys as LLMConfig)"
    )
    prompts: PromptsConfig | None = Field(
        default=None, description="Agent-specific prompts config overrides (same keys as PromptsConfig)"
    )
    config: AgentConfig = Field(default=AgentConfig(), description="Agent execution context configuration")
    tools: list[type[BaseTool] | str] = Field(default_factory=list, description="List of tool names to include")
    mcp_servers: MCPConfig = Field(
        default=MCPConfig,
        description="List of MCP server configurations. Read more about protocol here "
        "https://gofastmcp.com/clients/transports#mcp-json-configuration-transport",
    )

    @model_validator(mode="before")
    def defaults_validator(cls, data):
        data["openai"] = get_config().openai.model_copy(update=data.get("openai", {}))
        data["prompts"] = get_config().prompts.model_copy(update=data.get("prompts", {}))
        data["mcp_servers"] = data.get("mcp_servers", {}) or get_config().mcp.transport_config
        return data


class AgentsConfig(BaseModel):
    agents: list[AgentDefinition] = Field(default_factory=list, description="List of agent definitions")

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> Self:
        if not yaml_path.exists():
            return cls()

        with open(yaml_path, "r", encoding="utf-8") as f:
            return cls(**yaml.safe_load(f))


@cache
def get_agents_config() -> AgentsConfig:
    return AgentsConfig.from_yaml(Path(get_config().agents_config_path))
