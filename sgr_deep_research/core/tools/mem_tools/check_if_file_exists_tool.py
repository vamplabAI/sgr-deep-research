"""
Инструмент для проверки существования файла в памяти агента.

Проверяет существует ли файл по указанному пути.
"""

import os

from pydantic import Field

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.models import ResearchContext
from sgr_deep_research.core.tools.mem_tools.settings import MEMORY_PATH


class CheckIfFileExistsTool(BaseTool):
    """
    Проверяем существование файла по указанному пути, чтобы определить доступность данных.

    Args:
        reasoning: Обоснование необходимости проверки (1-2 предложения)
        file_path: Путь к файлу для проверки

    Returns:
        "True" если файл существует и является файлом, "False" иначе
    """

    reasoning: str = Field(
        description="Why do you need check file existence? (1-2 sentences MAX)",
        max_length=200
    )
    file_path: str = Field(description="The path to the file")

    async def __call__(self, context: ResearchContext, config=None, **kwargs) -> str:
        """
        Выполняем проверку существования файла, обрабатывая возможные исключения для надежности.

        Args:
            context: Контекст исследования агента
            config: Конфигурация агента (опционально)
            **kwargs: Дополнительные параметры

        Returns:
            Строка с результатом проверки
        """
        final_path = os.path.join(MEMORY_PATH, self.file_path)
        try:
            return str(os.path.exists(final_path) and os.path.isfile(final_path))
        except (OSError, TypeError, ValueError):
            return "False"

