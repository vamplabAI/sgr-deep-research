"""Application settings module using Pydantic Settings.

Loads configuration from YAML file with environment variables support.

Environment variables can override YAML settings using the format:
    OPENAI__API_KEY, TAVILY__API_KEY, etc.
"""

import logging
import logging.config
import os
from functools import cache
from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenAIConfig(BaseSettings):
    api_key: str = Field(description="API key")
    base_url: str = Field(default="https://api.openai.com/v1", description="Base URL")
    model: str = Field(default="gpt-4o-mini", description="Model to use")
    max_tokens: int = Field(default=8000, description="Maximum number of tokens")
    temperature: float = Field(default=0.4, ge=0.0, le=1.0, description="Generation temperature")
    proxy: str = Field(default="", description="Proxy URL (e.g., socks5://127.0.0.1:1081 or http://127.0.0.1:8080)")


class TavilyConfig(BaseSettings):
    api_key: str = Field(description="Tavily API key")
    api_base_url: str = Field(default="https://api.tavily.com", description="Tavily API base URL")


class SearchConfig(BaseSettings):
    max_results: int = Field(default=10, ge=1, description="Maximum number of search results")


class ScrapingConfig(BaseSettings):
    enabled: bool = Field(default=False, description="Enable full text scraping")
    max_pages: int = Field(default=5, gt=0, description="Maximum pages to scrape")
    content_limit: int = Field(default=1500, gt=0, description="Content character limit per source")


class PromptsConfig(BaseSettings):
    system_prompt_file: str = Field(default="prompts/system_prompt.txt", description="Path to system prompt file")
    initial_user_request_file: str = Field(
        default="prompts/initial_user_request.txt", description="Path to initial user request file"
    )
    clarification_response_file: str = Field(
        default="prompts/clarification_response.txt", description="Path to clarification response file"
    )


class ExecutionConfig(BaseSettings):
    max_steps: int = Field(default=6, gt=0, description="Maximum number of execution steps")


class LoggingConfig(BaseSettings):
    config_file: str = Field(default="logging_config.yaml", description="Logging configuration file path")
    logs_dir: str = Field(default="logs", description="Directory for saving bot logs")
    reports_dir: str = Field(default="reports", description="Directory for saving reports")


class MCPConfig(BaseSettings):
    context_limit: int = Field(default=15000, gt=0, description="Maximum context length from MCP server response")
    transport_config: dict = Field(default_factory=dict, description="MCP servers configuration")


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        case_sensitive=False,
        env_nested_delimiter="__",
    )

    openai: OpenAIConfig = Field(default_factory=OpenAIConfig, description="OpenAI settings")
    tavily: TavilyConfig = Field(default_factory=TavilyConfig, description="Tavily settings")
    search: SearchConfig = Field(default_factory=SearchConfig, description="Search settings")
    scraping: ScrapingConfig = Field(default_factory=ScrapingConfig, description="Scraping settings")
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig, description="Execution settings")
    prompts: PromptsConfig = Field(default_factory=PromptsConfig, description="Prompts settings")
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="Logging settings")
    mcp: MCPConfig = Field(default_factory=MCPConfig, description="MCP settings")
    agents_config_path: str = Field(default="agents.yaml", description="Agents configuration file path")

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "AppConfig":
        if not yaml_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")

        with open(yaml_path, "r", encoding="utf-8") as f:
            return cls(**yaml.safe_load(f))


class ServerConfig(BaseSettings):
    host: str = Field(default="0.0.0.0", description="Host to listen on")
    port: int = Field(default=8010, gt=0, le=65535, description="Port to listen on")


@cache
def get_config() -> AppConfig:
    app_config_env: str = os.environ.get("APP_CONFIG", "config.yaml")
    return AppConfig.from_yaml(Path(app_config_env))


def setup_logging() -> None:
    """Setup logging configuration from YAML file."""
    logging_config_path = Path(get_config().logging.config_file)
    if not logging_config_path.exists():
        raise FileNotFoundError(f"Logging config file not found: {logging_config_path}")

    with open(logging_config_path, "r", encoding="utf-8") as f:
        logging_config = yaml.safe_load(f)

    logs_dir = Path(get_config().logging.logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    reports_dir = Path(get_config().logging.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(logging_config)
