"""Инструмент для поиска в конкретном пространстве Confluence."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar

from pydantic import Field

from sgr_agent_core.base_tool import BaseTool
from sgr_agent_core.services.confluence_service import ConfluenceService

if TYPE_CHECKING:
    from sgr_agent_core.agent_definition import AgentConfig
    from sgr_agent_core.models import AgentContext

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ConfluenceSpaceFullTextSearchTool(BaseTool):
    """Полнотекстовый поиск в конкретном пространстве Confluence для целевой информации.

    Используйте, когда знаете конкретное пространство (область проекта/команды) для поиска.
    Более точный, чем общий поиск, когда пространство известно.
    
    Примечание: Когда include_content=True, контент ограничен превью (500 символов).
    Для полного контента с пагинацией используйте ConfluencePageRetrievalTool с конкретным page_id.
    """

    tool_name: ClassVar[str] = "ConfluenceSpaceFullTextSearchTool"

    reasoning: str = Field(description="Почему ищем в этом конкретном пространстве")
    query: str = Field(description="Поисковый запрос на том же языке, что и запрос пользователя")
    space_key: str = Field(description="Ключ пространства Confluence")
    max_results: int = Field(default=10, description="Максимальное количество результатов", ge=1, le=25)
    include_content: bool = Field(
        default=False,
        description="Включить превью контента (500 символов). Для полного контента используйте ConfluencePageRetrievalTool.",
    )

    def __init__(self, **data):
        """
        Инициализируем инструмент поиска в пространстве, чтобы подготовить сервис Confluence.
        
        Args:
            **data: Параметры инструмента
        """
        super().__init__(**data)
        self._confluence_service = ConfluenceService()

    async def __call__(self, context: AgentContext, config: AgentConfig, **_) -> str:
        """
        Выполняем поиск в пространстве Confluence, чтобы найти релевантные страницы.
        
        Args:
            context: Контекст агента для добавления источников
            config: Конфигурация агента
            
        Returns:
            str: Отформатированные результаты поиска с превью контента
        """
        logger.info(f"🔍 Confluence space search: '{self.query}' in space '{self.space_key}'")

        # Выполняем поиск в Confluence, чтобы получить список страниц
        result = self._confluence_service.search(
            query=self.query,
            limit=self.max_results,
            space=self.space_key,
            content_type="page",
            include_content=self.include_content,
        )

        # Добавляем найденные страницы в источники, чтобы обеспечить цитирование
        from sgr_agent_core.models import SourceData

        starting_number = len(context.sources) + 1
        for i, page in enumerate(result.pages, starting_number):
            source = SourceData(
                number=i,
                title=page.title,
                url=page.url,
                snippet=page.text_content[:500] if page.text_content else f"{page.space_name or ''} - {page.type}",
                full_content=page.text_content or "",
                char_count=len(page.text_content) if page.text_content else 0,
            )
            context.sources[page.url] = source

        # Формируем заголовок результатов, чтобы показать статистику поиска
        formatted_result = f"Confluence Space Search\n"
        formatted_result += f"Query: {self.query}\n"
        formatted_result += f"Space: {self.space_key}\n"
        formatted_result += f"Total Found: {result.total_size} pages\n"
        formatted_result += f"Showing: {len(result.pages)} results\n\n"

        formatted_result += "Results:\n\n"

        # Форматируем каждую найденную страницу, чтобы показать ключевую информацию
        for i, page in enumerate(result.pages, 1):
            formatted_result += f"[{i}] {page.title}\n"
            formatted_result += f"    Page ID: {page.id}\n"
            formatted_result += f"    URL: {page.url}\n"
            if page.version:
                formatted_result += f"    Version: {page.version}\n"
            if page.last_updated:
                formatted_result += f"    Updated: {page.last_updated}"
                if page.author:
                    formatted_result += f" by {page.author}"
                formatted_result += "\n"
            
            # Показываем превью контента, чтобы дать представление о содержимом
            if self.include_content and page.text_content:
                content_preview = page.text_content[:500]
                total_chars = len(page.text_content)
                formatted_result += f"    Content Preview ({total_chars:,} chars total):\n"
                formatted_result += f"    {content_preview}"
                if total_chars > 500:
                    formatted_result += "...\n"
                    formatted_result += f"    💡 Use ConfluencePageRetrievalTool with page_id='{page.id}' for full paginated content\n"
                else:
                    formatted_result += "\n"
            formatted_result += "\n"

        logger.info(f"✅ Found {len(result.pages)} pages in space {self.space_key}, added to sources")
        return formatted_result
