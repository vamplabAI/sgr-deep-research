"""Инструмент для получения контента конкретной страницы Confluence."""

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


class ConfluencePageRetrievalTool(BaseTool):
    """Получение контента конкретной страницы Confluence по ID с поддержкой пагинации.

    Используйте, когда у вас есть ID страницы из результатов поиска и нужен контент страницы.
    Для больших страниц контент разбивается на части для удобной обработки.

    Получить ID страницы можно из:
    - Предыдущих результатов ConfluenceFullTextSearchTool (поле 'Page ID')
    - Предыдущих результатов ConfluenceSpaceFullTextSearchTool (поле 'Page ID')
    - Прямого URL (параметр pageId в URL)

    ВАЖНО: ID страницы должен быть числовой строкой типа '4266429013', НЕ ключи пространств типа 'GPP' или пути типа 'GPP/PageName'.

    Пагинация:
    - Контент автоматически разбивается на части (по умолчанию 4000 символов)
    - Используйте page_number для навигации между частями (начиная с 1)
    - Ответ показывает общее количество страниц и текущий номер страницы
    """

    tool_name: ClassVar[str] = "ConfluencePageRetrievalTool"

    reasoning: str = Field(description="Почему получаем эту конкретную страницу")
    page_id: str = Field(
        description="ID страницы Confluence - ДОЛЖЕН быть числовой строкой типа '4266429013'. "
        "Получите его из результатов поиска в поле 'Page ID' или из параметра 'pageId' в URL. "
        "НЕ ключ пространства (типа 'GPP')."
    )
    page_number: int = Field(
        default=1,
        description="Номер страницы для получения (начиная с 1). Используйте для навигации по большому контенту.",
        ge=1,
    )
    chunk_size: int = Field(
        default=4000,
        description="Символов на одну часть. По умолчанию 4000 для оптимального использования контекста.",
        ge=1000,
        le=10000,
    )

    def __init__(self, **data):
        """
        Инициализируем инструмент получения страницы, чтобы подготовить сервис Confluence.
        
        Args:
            **data: Параметры инструмента
        """
        super().__init__(**data)
        self._confluence_service = ConfluenceService()

    async def __call__(self, context: AgentContext, config: AgentConfig, **_) -> str:
        """
        Получаем контент страницы Confluence с пагинацией, чтобы не перегружать контекст.
        
        Args:
            context: Контекст агента для добавления источников
            config: Конфигурация агента
            
        Returns:
            str: Отформатированный контент страницы с информацией о пагинации
        """

        # Валидируем формат page_id, чтобы избежать ошибок
        if not self.page_id.isdigit():
            error_msg = (
                f"❌ Invalid page_id format: '{self.page_id}'\n\n"
                f"Page ID must be numeric (e.g., '4266429013'), not a space key or path.\n"
                f"To get the correct page ID:\n"
                f"1. Use ConfluenceFullTextSearchTool or ConfluenceSpaceFullTextSearchTool first\n"
                f"2. Look for 'Page ID' field in results\n"
                f"3. Use that numeric ID with this tool\n\n"
                f"Example: If search shows 'Page ID: 4266429013', use '4266429013' not 'GPP/Zmn'."
            )
            logger.error(error_msg)
            return error_msg

        logger.info(f"📄 Retrieving Confluence page: {self.page_id}, page {self.page_number}")
        
        # Получаем страницу из Confluence, чтобы извлечь контент
        try:
            page = self._confluence_service.get_page(
                page_id=self.page_id,
                include_content=True,
            )
        except Exception as e:
            error_msg = (
                f"❌ Failed to retrieve page {self.page_id}: {str(e)}\n\n"
                f"Possible reasons:\n"
                f"- Page doesn't exist or was deleted\n"
                f"- No access permissions to this page\n"
                f"- Invalid page ID\n\n"
                f"Try using ConfluenceFullTextSearchTool to find the correct page."
            )
            logger.error(error_msg)
            return error_msg

        # Добавляем страницу в источники контекста, чтобы обеспечить цитирование
        from sgr_agent_core.models import SourceData

        if page.url not in context.sources:
            starting_number = len(context.sources) + 1
            source = SourceData(
                number=starting_number,
                title=page.title,
                url=page.url,
                snippet=page.text_content[:500] if page.text_content else f"{page.space_name or ''} - {page.type}",
                full_content=page.text_content or "",
                char_count=len(page.text_content) if page.text_content else 0,
            )
            context.sources[page.url] = source

        # Формируем заголовок результата, чтобы показать метаданные страницы
        formatted_result = f"Confluence Page\n"
        formatted_result += f"{'='*80}\n\n"
        formatted_result += f"Title: {page.title}\n"
        formatted_result += f"ID: {page.id}\n"
        formatted_result += f"Type: {page.type}\n"
        if page.space_name:
            formatted_result += f"Space: {page.space_name} ({page.space_key})\n"
        formatted_result += f"URL: {page.url}\n"
        if page.version:
            formatted_result += f"Version: {page.version}\n"
        if page.last_updated:
            formatted_result += f"Last Updated: {page.last_updated}"
            if page.author:
                formatted_result += f" by {page.author}"
            formatted_result += "\n"

        # Обрабатываем пагинацию контента, чтобы разбить большой текст на части
        if page.text_content:
            content = page.text_content
            total_chars = len(content)
            total_pages = (total_chars + self.chunk_size - 1) // self.chunk_size  # Округляем вверх
            
            # Проверяем валидность номера страницы, чтобы избежать выхода за границы
            if self.page_number > total_pages:
                formatted_result += f"\n{'='*80}\n\n"
                formatted_result += f"⚠️ Page {self.page_number} does not exist.\n"
                formatted_result += f"Total pages available: {total_pages}\n"
                formatted_result += f"Total characters: {total_chars:,}\n"
                formatted_result += f"\nPlease use page_number between 1 and {total_pages}.\n"
                logger.warning(f"⚠️ Invalid page number {self.page_number} for page {self.page_id}")
                return formatted_result
            
            # Вычисляем границы текущего чанка, чтобы извлечь нужную порцию
            start_idx = (self.page_number - 1) * self.chunk_size
            end_idx = min(start_idx + self.chunk_size, total_chars)
            content_chunk = content[start_idx:end_idx]
            
            # Добавляем информацию о пагинации, чтобы агент знал о доступных страницах
            formatted_result += f"\n{'='*80}\n\n"
            formatted_result += f"📊 Pagination Info:\n"
            formatted_result += f"   Total Content Size: {total_chars:,} characters\n"
            formatted_result += f"   Total Pages: {total_pages}\n"
            formatted_result += f"   Current Page: {self.page_number}/{total_pages}\n"
            formatted_result += f"   Chunk Size: {self.chunk_size} characters\n"
            formatted_result += f"   Showing: characters {start_idx:,} to {end_idx:,}\n"
            
            if self.page_number < total_pages:
                formatted_result += f"\n💡 To see more content, call this tool again with page_number={self.page_number + 1}\n"
            
            formatted_result += f"\n{'='*80}\n\n"
            formatted_result += "Content:\n\n"
            formatted_result += content_chunk
            
            logger.info(
                f"✅ Retrieved page: {page.title}, "
                f"page {self.page_number}/{total_pages}, "
                f"chars {start_idx}-{end_idx}/{total_chars}"
            )
        else:
            formatted_result += f"\n{'='*80}\n\n"
            formatted_result += "No content available.\n"
            logger.info(f"✅ Retrieved page: {page.title} (no content)")

        return formatted_result
