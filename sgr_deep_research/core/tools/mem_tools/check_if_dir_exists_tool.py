"""
Инструмент для проверки существования директории в памяти агента.

Проверяет существует ли директория по указанному пути.
"""

import os

from pydantic import Field

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.models import ResearchContext
from sgr_deep_research.core.tools.mem_tools.settings import MEMORY_PATH


class CheckIfDirExistsTool(BaseTool):
    """
    Проверяем существование директории по указанному пути, чтобы определить доступность структуры.

    Args:
        reasoning: Обоснование необходимости проверки (1-2 предложения)
        dir_path: Путь к директории для проверки

    Returns:
        "True" если директория существует и является директорией, "False" иначе
    """

    reasoning: str = Field(
        description="Why do you need check directory existence? (1-2 sentences MAX)",
        max_length=200
    )
    dir_path: str = Field(description="The path to the directory")

    async def __call__(self, context: ResearchContext, config=None, **kwargs) -> str:
        """
        Выполняем проверку существования директории, обрабатывая возможные исключения для надежности.

        Args:
            context: Контекст исследования агента
            config: Конфигурация агента (опционально)
            **kwargs: Дополнительные параметры

        Returns:
            Строка с результатом проверки
        """
        final_path = os.path.join(MEMORY_PATH, self.dir_path)
        try:
            return str(os.path.exists(final_path) and os.path.isdir(final_path))
        except (OSError, TypeError, ValueError):
            return "False"

