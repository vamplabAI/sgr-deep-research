"""Application settings module using Pydantic and EnvYAML.

Loads configuration from YAML file with environment variables support.
"""

import logging
import logging.config
import os
from functools import cache
from pathlib import Path

import yaml
from envyaml import EnvYAML
from pydantic import BaseModel, Field


class OpenAIConfig(BaseModel):
    """OpenAI API settings."""

    api_key: str = Field(description="API key")
    base_url: str = Field(default="https://api.openai.com/v1", description="Base URL")
    model: str = Field(default="gpt-4o-mini", description="Model to use")
    max_tokens: int = Field(default=8000, description="Maximum number of tokens")
    temperature: float = Field(default=0.4, ge=0.0, le=1.0, description="Generation temperature")
    proxy: str = Field(default="", description="Proxy URL (e.g., socks5://127.0.0.1:1081 or http://127.0.0.1:8080)")


class TavilyConfig(BaseModel):
    """Tavily Search API settings."""

    api_key: str = Field(description="Tavily API key")
    api_base_url: str = Field(default="https://api.tavily.com", description="Tavily API base URL")


class SearchConfig(BaseModel):
    """Search settings."""

    max_results: int = Field(default=10, ge=1, description="Maximum number of search results")


class ScrapingConfig(BaseModel):
    """Web scraping settings."""

    enabled: bool = Field(default=False, description="Enable full text scraping")
    max_pages: int = Field(default=5, gt=0, description="Maximum pages to scrape")
    content_limit: int = Field(default=1500, gt=0, description="Content character limit per source")


class PromptsConfig(BaseModel):
    """Prompts settings."""

    prompts_dir: str = Field(default="prompts", description="Directory with prompts")
    system_prompt_file: str = Field(default="system_prompt.txt", description="System prompt file")


class ExecutionConfig(BaseModel):
    """Application execution settings."""

    max_steps: int = Field(default=6, gt=0, description="Maximum number of execution steps")
    reports_dir: str = Field(default="reports", description="Directory for saving reports")
    logs_dir: str = Field(default="logs", description="Directory for saving bot logs")


class LoggingConfig(BaseModel):
    """Logging configuration settings."""

    config_file: str = Field(default="logging_config.yaml", description="Logging configuration file path")


class MCPConfig(BaseModel):
    """MCP (Model Context Protocol) configuration settings."""

    context_limit: int = Field(default=15000, gt=0, description="Maximum context length from MCP server response")
    transport_config: dict = Field(default_factory=dict, description="MCP servers configuration")


class AppConfig(BaseModel):
    """Main application configuration."""

    openai: OpenAIConfig = Field(description="OpenAI settings")
    tavily: TavilyConfig = Field(description="Tavily settings")
    search: SearchConfig = Field(default_factory=SearchConfig, description="Search settings")
    scraping: ScrapingConfig = Field(default_factory=ScrapingConfig, description="Scraping settings")
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig, description="Execution settings")
    prompts: PromptsConfig = Field(default_factory=PromptsConfig, description="Prompts settings")
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="Logging settings")
    mcp: MCPConfig = Field(default_factory=MCPConfig, description="MCP settings")


class ServerConfig(BaseModel):
    """Server configuration."""

    host: str = Field(default="0.0.0.0", description="Host to listen on")
    port: int = Field(default=8010, gt=0, le=65535, description="Port to listen on")


@cache
def get_config() -> AppConfig:
    app_config_env: str = os.environ.get("APP_CONFIG", "config.yaml")

    # If path has no directory part, assume it's in current working directory
    if os.path.basename(app_config_env) == app_config_env:
        app_config_path = Path.cwd() / app_config_env
    else:
        app_config_path = Path(app_config_env)

    return AppConfig.model_validate(dict(EnvYAML(str(app_config_path))))


def setup_logging() -> None:
    """Setup logging configuration from YAML file."""
    logging_config_path = Path(get_config().logging.config_file)
    if not logging_config_path.exists():
        raise FileNotFoundError(f"Logging config file not found: {logging_config_path}")

    with open(logging_config_path, "r", encoding="utf-8") as f:
        logging_config = yaml.safe_load(f)

    logs_dir = Path(get_config().execution.logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    reports_dir = Path(get_config().execution.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(logging_config)
