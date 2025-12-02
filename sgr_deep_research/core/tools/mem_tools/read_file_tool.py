"""
Инструмент для чтения файлов из памяти агента.

Читает содержимое файла и возвращает его в виде строки.
"""

import os

from pydantic import Field

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.models import ResearchContext
from sgr_deep_research.core.tools.mem_tools.settings import MEMORY_PATH


class ReadFileTool(BaseTool):
    """
    Читаем файл из памяти, чтобы получить доступ к сохраненным данным.

    Args:
        reasoning: Обоснование необходимости чтения файла (1-2 предложения)
        file_path: Путь к файлу для чтения

    Returns:
        Содержимое файла или сообщение об ошибке если файл не может быть прочитан
    """

    reasoning: str = Field(
        description="Why do you need read file? (1-2 sentences MAX)",
        max_length=200
    )
    file_path: str = Field(description="The path to the file.")

    async def __call__(self, context: ResearchContext, config=None, **kwargs) -> str:
        """
        Выполняем чтение файла, проверяя его существование для безопасности.

        Args:
            context: Контекст исследования агента
            config: Конфигурация агента (опционально)
            **kwargs: Дополнительные параметры

        Returns:
            Содержимое файла или описание ошибки
        """
        final_path = os.path.join(MEMORY_PATH, self.file_path)
        try:
            if not os.path.exists(final_path):
                return f"Error: File {final_path} does not exist"

            if not os.path.isfile(final_path):
                return f"Error: {final_path} is not a file"

            with open(final_path, "r") as f:
                return f.read()
        except PermissionError:
            return f"Error: Permission denied accessing {final_path}"
        except Exception as e:
            return f"Error: {e}"

