"""Confluence API service для поиска и получения внутренней документации."""

from __future__ import annotations

import logging
import re
from typing import Literal

import httpx
from pydantic import BaseModel, Field

from sgr_agent_core.agent_config import GlobalConfig

logger = logging.getLogger(__name__)


class ConfluencePage(BaseModel):
    """Модель данных страницы Confluence."""

    id: str = Field(description="ID страницы")
    title: str = Field(description="Заголовок страницы")
    type: str = Field(default="page", description="Тип контента (page, blogpost, attachment)")
    url: str = Field(description="URL страницы")
    space_key: str | None = Field(default=None, description="Ключ пространства")
    space_name: str | None = Field(default=None, description="Название пространства")
    version: int | None = Field(default=None, description="Номер версии страницы")
    last_updated: str | None = Field(default=None, description="Время последнего обновления")
    author: str | None = Field(default=None, description="Имя последнего автора")
    text_content: str | None = Field(default=None, description="Полный текстовый контент")


class ConfluenceSearchResult(BaseModel):
    """Результат поиска в Confluence с найденными страницами и метаданными."""

    pages: list[ConfluencePage] = Field(default_factory=list, description="Найденные страницы")
    total_size: int = Field(default=0, description="Общее количество результатов")
    search_duration: int | None = Field(default=None, description="Длительность поиска в мс")


class ConfluenceService:
    """Сервис для взаимодействия с Confluence API."""

    def __init__(self):
        """
        Инициализируем сервис Confluence, чтобы подключиться к API.
        
        Raises:
            ValueError: Если конфигурация Confluence не найдена в config.yaml
        """
        config = GlobalConfig()
        if not hasattr(config, "confluence"):
            raise ValueError(
                "Confluence configuration not found in config.yaml. "
                "Please add 'confluence' section with base_url, username, and password."
            )

        self.base_url = config.confluence.base_url.rstrip("/")
        self.username = config.confluence.username
        self.password = config.confluence.password
        self.timeout = getattr(config.confluence, "timeout", 30.0)

        # Создаем HTTP клиент, чтобы выполнять запросы к API
        self._client = httpx.Client(
            auth=(self.username, self.password),
            timeout=self.timeout,
            headers={"Accept": "application/json"},
        )

    def search(
        self,
        query: str,
        limit: int = 10,
        space: str | None = None,
        content_type: Literal["page", "blogpost", "attachment"] = "page",
        include_content: bool = False,
    ) -> ConfluenceSearchResult:
        """
        Ищем в Confluence используя CQL (Confluence Query Language), чтобы найти релевантные страницы.

        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            space: Опциональный ключ пространства для поиска
            content_type: Тип контента для поиска
            include_content: Включить полный контент страницы

        Returns:
            ConfluenceSearchResult: Результат с найденными страницами
        """
        # Строим CQL запрос, чтобы сформировать правильный поисковый запрос
        cql_parts = [f'type="{content_type}"']

        if space:
            cql_parts.append(f'space="{space}"')

        # Добавляем текстовый поиск
        cql_parts.append(f'text ~ "{query}"')

        cql = " AND ".join(cql_parts)

        # Формируем параметры запроса, чтобы получить нужные данные
        params = {
            "cql": cql,
            "limit": limit,
            "expand": "space,version,history.lastUpdated",
        }

        logger.info(f"🔍 Confluence CQL search: {cql}")

        try:
            # Выполняем запрос к API, чтобы получить результаты поиска
            response = self._client.get(f"{self.base_url}/rest/api/content/search", params=params)
            response.raise_for_status()
            data = response.json()

            # Парсим результаты, чтобы преобразовать их в модели
            pages = []
            for result in data.get("results", []):
                page = self._parse_page_result(result, include_content=include_content)
                pages.append(page)

            search_result = ConfluenceSearchResult(
                pages=pages,
                total_size=data.get("totalSize", 0),
                search_duration=data.get("searchDuration"),
            )

            logger.info(f"✅ Found {len(pages)} Confluence pages")
            return search_result

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Confluence API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"❌ Confluence search failed: {e}")
            raise

    def get_page(self, page_id: str, include_content: bool = True) -> ConfluencePage:
        """
        Получаем конкретную страницу Confluence по ID, чтобы извлечь её контент.

        Args:
            page_id: ID страницы
            include_content: Включить полный контент страницы

        Returns:
            ConfluencePage: Данные страницы
        """
        params = {"expand": "space,version,history.lastUpdated,body.storage"}

        logger.info(f"📄 Retrieving Confluence page: {page_id}")

        try:
            # Запрашиваем страницу из API, чтобы получить её данные
            response = self._client.get(f"{self.base_url}/rest/api/content/{page_id}", params=params)
            response.raise_for_status()
            data = response.json()

            page = self._parse_page_result(data, include_content=include_content)

            logger.info(f"✅ Retrieved page: {page.title}")
            return page

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Confluence API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to retrieve page: {e}")
            raise

    def _parse_page_result(self, result: dict, include_content: bool = False) -> ConfluencePage:
        """
        Парсим результат Confluence API в модель ConfluencePage, чтобы структурировать данные.
        
        Args:
            result: Словарь с данными страницы из API
            include_content: Включить текстовый контент
            
        Returns:
            ConfluencePage: Структурированная модель страницы
        """
        page_id = result.get("id", "")
        title = result.get("title", "")
        content_type = result.get("type", "page")

        # Строим URL страницы, чтобы обеспечить доступ к ней
        url = f"{self.base_url}/wiki/spaces/{result.get('space', {}).get('key', '')}/pages/{page_id}"
        if "_links" in result and "webui" in result["_links"]:
            url = self.base_url + result["_links"]["webui"]

        # Извлекаем информацию о пространстве
        space_data = result.get("space", {})
        space_key = space_data.get("key")
        space_name = space_data.get("name")

        # Извлекаем информацию о версии
        version_data = result.get("version", {})
        version = version_data.get("number")

        # Извлекаем информацию о последнем обновлении
        history = result.get("history", {})
        last_updated_data = history.get("lastUpdated", {})
        last_updated = last_updated_data.get("when")
        author_data = last_updated_data.get("by", {})
        author = author_data.get("displayName")

        # Извлекаем контент, если запрошено
        text_content = None
        if include_content:
            body = result.get("body", {})
            storage = body.get("storage", {})
            html_content = storage.get("value", "")

            # Простое преобразование HTML в текст (удаляем теги), чтобы получить чистый текст
            text_content = re.sub(r"<[^>]+>", "", html_content)
            text_content = re.sub(r"\s+", " ", text_content).strip()

        return ConfluencePage(
            id=page_id,
            title=title,
            type=content_type,
            url=url,
            space_key=space_key,
            space_name=space_name,
            version=version,
            last_updated=last_updated,
            author=author,
            text_content=text_content,
        )

    def __del__(self):
        """Закрываем HTTP клиент при очистке, чтобы освободить ресурсы."""
        if hasattr(self, "_client"):
            self._client.close()
