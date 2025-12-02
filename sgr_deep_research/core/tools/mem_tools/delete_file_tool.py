"""
Инструмент для удаления файлов из памяти агента.

Удаляет файл по указанному пути.
"""

import os

from pydantic import Field

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.models import ResearchContext
from sgr_deep_research.core.tools.mem_tools.settings import MEMORY_PATH


class DeleteFileTool(BaseTool):
    """
    Удаляем файл из памяти, чтобы освободить место или убрать устаревшие данные.

    Args:
        reasoning: Обоснование необходимости удаления файла (1-2 предложения)
        file_path: Путь к файлу для удаления

    Returns:
        "True" если файл удален успешно, "False" иначе
    """

    reasoning: str = Field(
        description="Why do you need delete file? (1-2 sentences MAX)",
        max_length=200
    )
    file_path: str = Field(description="The path to the file.")

    async def __call__(self, context: ResearchContext, config=None, **kwargs) -> str:
        """
        Выполняем удаление файла, обрабатывая возможные ошибки для безопасности.

        Args:
            context: Контекст исследования агента
            config: Конфигурация агента (опционально)
            **kwargs: Дополнительные параметры

        Returns:
            Строка с результатом операции
        """
        final_path = os.path.join(MEMORY_PATH, self.file_path)
        try:
            os.remove(final_path)
            return "True"
        except Exception:
            return "False"

