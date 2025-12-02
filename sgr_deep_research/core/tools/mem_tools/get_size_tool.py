"""
Инструмент для получения размера файла или директории в памяти агента.

Вычисляет размер файла или суммарный размер всех файлов в директории.
"""

import os

from pydantic import Field

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.models import ResearchContext
from sgr_deep_research.core.tools.mem_tools.settings import MEMORY_PATH


class GetSizeTool(BaseTool):
    """
    Получаем размер файла или директории, чтобы контролировать использование памяти.

    Args:
        reasoning: Обоснование необходимости получения размера (1-2 предложения)
        file_or_dir_path: Путь к файлу или директории.
                         Если пустая строка, возвращает общий размер директории памяти

    Returns:
        Размер файла или директории в байтах
    """

    reasoning: str = Field(
        description="Why do you need get size? (1-2 sentences MAX)",
        max_length=200
    )
    file_or_dir_path: str = Field(description="The path to the file or directory.")

    async def __call__(self, context: ResearchContext, config=None, **kwargs) -> str:
        """
        Выполняем вычисление размера, рекурсивно обходя директории для точного подсчета.

        Args:
            context: Контекст исследования агента
            config: Конфигурация агента (опционально)
            **kwargs: Дополнительные параметры

        Returns:
            Строка с размером в байтах
        """
        final_path = os.path.join(MEMORY_PATH, self.file_or_dir_path)

        if not final_path or final_path == "" or final_path == MEMORY_PATH:
            cwd = MEMORY_PATH
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(cwd):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                    except OSError:
                        pass
            return str(total_size)

        if os.path.isfile(final_path):
            return str(os.path.getsize(final_path))
        elif os.path.isdir(final_path):
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(final_path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                    except OSError:
                        pass
            return str(total_size)
        else:
            raise FileNotFoundError(f"Path not found: {final_path}")

