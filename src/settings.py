"""
Модуль настроек приложения с использованием Pydantic и EnvYAML.
Загружает конфигурацию из YAML файла с поддержкой переменных окружения.
"""

import os
from pathlib import Path
from functools import cache

from envyaml import EnvYAML
from pydantic import BaseModel, Field


class OpenAIConfig(BaseModel):
    """Настройки OpenAI API."""

    api_key: str = Field(description="API ключ")
    base_url: str = Field(default="https://api.openai.com/v1", description="Базовый URL")
    model: str = Field(default="gpt-4o-mini", description="Модель для использования")
    max_tokens: int = Field(default=8000, description="Максимальное количество токенов")
    temperature: float = Field(default=0.4, ge=0.0, le=1.0, description="Температура генерации")
    proxy: str = Field(default="", description="Proxy URL (e.g., socks5://127.0.0.1:1081 or http://127.0.0.1:8080)")


class TavilyConfig(BaseModel):
    """Настройки Tavily Search API."""

    api_key: str = Field(description="Tavily API ключ")


class SearchConfig(BaseModel):
    """Настройки поиска."""

    max_results: int = Field(default=10, ge=1, description="Максимальное количество результатов поиска")


class ScrapingConfig(BaseModel):
    """Настройки скрепинга веб-страниц."""

    enabled: bool = Field(default=False, description="Включить скрепинг полного текста")
    max_pages: int = Field(default=5, gt=0, description="Максимум страниц для скрепинга")
    content_limit: int = Field(default=1500, gt=0, description="Лимит символов контента на источник")


class PromptsConfig(BaseModel):
    """Настройки промптов."""

    prompts_dir: str = Field(default="prompts", description="Директория с промптами")
    tool_function_prompt_file: str = Field(
        default="tool_function_prompt.txt", description="Файл промпта для функций инструментов"
    )
    system_prompt_file: str = Field(default="system_prompt.txt", description="Файл системного промпта")


class ExecutionConfig(BaseModel):
    """Настройки выполнения приложения."""

    max_steps: int = Field(default=6, gt=0, description="Максимальное количество шагов выполнения")
    reports_dir: str = Field(default="reports", description="Директория для сохранения отчетов")


class AppConfig(BaseModel):
    """Главная конфигурация приложения."""

    openai: OpenAIConfig = Field(description="Настройки OpenAI")
    tavily: TavilyConfig = Field(description="Настройки Tavily")
    search: SearchConfig = Field(default_factory=SearchConfig, description="Настройки поиска")
    scraping: ScrapingConfig = Field(default_factory=ScrapingConfig, description="Настройки скрепинга")
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig, description="Настройки выполнения")
    prompts: PromptsConfig = Field(default_factory=PromptsConfig, description="Настройки промптов")

    max_searches_total: int = Field(default=5, ge=1)
    max_rounds: int = Field(default=5, ge=1)


class ServerConfig(BaseModel):
    """Конфигурация сервера."""

    host: str = Field(default="0.0.0.0", description="Хост для прослушивания")
    port: int = Field(default=8010, gt=0, le=65535, description="Порт для прослушивания")


@cache
def get_config() -> AppConfig:
    app_config_env: str = os.environ.get("APP_CONFIG", "config.yaml")

    # If path has no directory part, assume it's in current working directory
    if os.path.basename(app_config_env) == app_config_env:
        app_config_path = Path.cwd() / app_config_env
    else:
        app_config_path = Path(app_config_env)

    return AppConfig.model_validate(dict(EnvYAML(str(app_config_path))))
