"""
Инструмент для создания директорий в памяти агента.

Создает новую директорию по указанному пути.
"""

import os

from pydantic import Field

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.models import ResearchContext
from sgr_deep_research.core.tools.mem_tools.settings import MEMORY_PATH


class CreateDirTool(BaseTool):
    """
    Создаем новую директорию в памяти, чтобы организовать структуру хранения файлов.

    Args:
        reasoning: Обоснование необходимости создания директории (1-2 предложения)
        dir_path: Путь к создаваемой директории

    Returns:
        "True" если директория создана успешно, "False" иначе
    """

    reasoning: str = Field(
        description="Why do you need create directory? (1-2 sentences MAX)",
        max_length=200
    )
    dir_path: str = Field(description="The path to the directory.")

    async def __call__(self, context: ResearchContext, config=None, **kwargs) -> str:
        """
        Выполняем создание директории, используя exist_ok для безопасного создания.

        Args:
            context: Контекст исследования агента
            config: Конфигурация агента (опционально)
            **kwargs: Дополнительные параметры

        Returns:
            Строка с результатом операции
        """
        final_path = os.path.join(MEMORY_PATH, self.dir_path)
        try:
            os.makedirs(final_path, exist_ok=True)
            return "True"
        except Exception:
            return "False"

