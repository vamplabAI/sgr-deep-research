"""Application settings module using Pydantic and EnvYAML.

Loads configuration from YAML file with environment variables support.
"""

import os
from functools import cache
from pathlib import Path

from envyaml import EnvYAML
from pydantic import BaseModel, Field
from typing import Optional


class OpenAIConfig(BaseModel):
    """OpenAI API settings."""

    api_key: str = Field(description="API key")
    base_url: str = Field(default="https://api.openai.com/v1", description="Base URL")
    model: str = Field(default="gpt-4o-mini", description="Model to use")
    max_tokens: int = Field(default=32000, description="Maximum number of tokens (for older models)")
    max_completion_tokens: int = Field(default=32000, description="Maximum completion tokens (for newer models like GPT-5)")
    temperature: float = Field(default=0.4, ge=0.0, le=1.0, description="Generation temperature")
    reasoning_effort: str = Field(default="medium", description="GPT-5 reasoning effort: low/medium/high")
    verbosity: str = Field(default="medium", description="GPT-5 verbosity level: low/medium/high")
    proxy: str = Field(default="", description="Proxy URL (e.g., socks5://127.0.0.1:1081 or http://127.0.0.1:8080)")


class AzureConfig(BaseModel):
    """Azure OpenAI API settings."""

    api_key: str = Field(description="Azure OpenAI API key")
    base_url: str = Field(description="Azure OpenAI endpoint URL")
    api_version: str = Field(default="2024-12-01-preview", description="Azure API version")
    deployment_name: str = Field(description="Azure deployment name")
    max_tokens: int = Field(default=32000, description="Maximum number of tokens (for older models)")
    max_completion_tokens: int = Field(default=32000, description="Maximum completion tokens (for newer models like GPT-5)")
    temperature: float = Field(default=0.4, ge=0.0, le=1.0, description="Generation temperature")
    reasoning_effort: str = Field(default="medium", description="GPT-5 reasoning effort: low/medium/high")
    verbosity: str = Field(default="medium", description="GPT-5 verbosity level: low/medium/high")
    proxy: str = Field(default="", description="Proxy URL (e.g., socks5://127.0.0.1:1081 or http://127.0.0.1:8080)")


class TavilyConfig(BaseModel):
    """Tavily Search API settings."""

    api_key: Optional[str] = Field(description="Tavily API key")
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
    tool_function_prompt_file: str = Field(default="tool_function_prompt.txt", description="Tool functions prompt file")
    system_prompt_file: str = Field(default="system_prompt.txt", description="System prompt file")


class ExecutionConfig(BaseModel):
    """Application execution settings."""

    max_steps: int = Field(default=6, gt=0, description="Maximum number of execution steps")
    reports_dir: str = Field(default="reports", description="Directory for saving reports")
    logs_dir: str = Field(default="logs", description="Directory for saving bot logs")


class DeepResearchConfig(BaseModel):
    """Deep research mode settings for intensive analysis."""

    enabled: bool = Field(default=False, description="Enable deep research mode")
    max_steps: int = Field(default=20, gt=0, description="Maximum research steps for deep mode")
    max_searches: int = Field(default=10, gt=0, description="Maximum number of search queries")
    max_results_per_search: int = Field(default=20, gt=0, description="Results per search query")
    enable_full_scraping: bool = Field(default=True, description="Enable full content scraping")
    scraping_limit: int = Field(default=5000, gt=0, description="Character limit per scraped page")
    cross_reference: bool = Field(default=True, description="Enable cross-referencing sources")
    synthesis_iterations: int = Field(default=3, gt=0, description="Number of synthesis passes")


class AppConfig(BaseModel):
    """Main application configuration."""

    openai: Optional[OpenAIConfig] = Field(default=None, description="OpenAI settings")
    azure: Optional[AzureConfig] = Field(default=None, description="Azure OpenAI settings")
    tavily: TavilyConfig = Field(description="Tavily settings")
    search: SearchConfig = Field(default_factory=SearchConfig, description="Search settings")
    scraping: ScrapingConfig = Field(default_factory=ScrapingConfig, description="Scraping settings")
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig, description="Execution settings")
    deep_research: DeepResearchConfig = Field(default_factory=DeepResearchConfig, description="Deep research settings")
    prompts: PromptsConfig = Field(default_factory=PromptsConfig, description="Prompts settings")


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
