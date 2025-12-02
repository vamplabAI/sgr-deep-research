"""
Инструмент для перехода по ссылкам в памяти агента.

Позволяет переходить по внутренним ссылкам в стиле Obsidian между заметками.
"""

import os

from pydantic import Field

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.models import ResearchContext
from sgr_deep_research.core.tools.mem_tools.settings import MEMORY_PATH


class GoToLinkTool(BaseTool):
    """
    Переходим по ссылке в памяти и возвращаем содержимое заметки Y, чтобы получить связанные данные.

    Ссылка в заметке X на заметку Y с путем path/to/note/Y.md структурирована так:
    [[path/to/note/Y]]

    Args:
        reasoning: Обоснование необходимости перехода по ссылке (1-2 предложения)
        link_string: Ссылка для перехода

    Returns:
        Содержимое заметки Y или сообщение об ошибке если ссылка недоступна
    """

    reasoning: str = Field(
        description="Why do you need follow this link? (1-2 sentences MAX)",
        max_length=200
    )
    link_string: str = Field(description="The string link to the file.")

    async def __call__(self, context: ResearchContext, config=None, **kwargs) -> str:
        """
        Выполняем переход по ссылке, обрабатывая ссылки в стиле Obsidian для совместимости.

        Args:
            context: Контекст исследования агента
            config: Конфигурация агента (опционально)
            **kwargs: Дополнительные параметры

        Returns:
            Содержимое связанного файла или описание ошибки
        """
        try:
            if self.link_string.startswith("[[") and self.link_string.endswith("]]"):
                file_path = self.link_string[2:-2]
                if not file_path.endswith('.md'):
                    file_path += '.md'
            else:
                file_path = self.link_string

            final_path = os.path.join(MEMORY_PATH, file_path)

            if not os.path.exists(final_path):
                return f"Error: File {final_path} not found"

            if not os.path.isfile(final_path):
                return f"Error: {final_path} is not a file"

            with open(final_path, "r") as f:
                return f.read()
        except PermissionError:
            return f"Error: Permission denied accessing {self.link_string}"
        except Exception as e:
            return f"Error: {e}"

