"""
Инструмент для обновления содержимого файлов в памяти агента.

Выполняет простую замену текста в файле методом find-and-replace.
"""

import os

from pydantic import Field

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.models import ResearchContext
from sgr_deep_research.core.tools.mem_tools.settings import MEMORY_PATH


class UpdateFileTool(BaseTool):
    """
    Обновляем файл методом простой замены текста, чтобы изменить его содержимое.

    Это упрощенная альтернатива write_to_file(), которая не требует создания
    git-style diffs. Выполняет простую замену строки.

    Args:
        reasoning: Обоснование необходимости обновления файла (1-2 предложения)
        file_path: Путь к файлу для обновления
        old_content: Точный текст для поиска и замены в файле
        new_content: Текст для замены old_content

    Returns:
        "True" если операция успешна, сообщение об ошибке если неудачна

    Examples:
        # Добавление новой строки в таблицу
        old = "| TKT-1056  | 2024-09-25 | Late Delivery   | Resolved |"
        new = "| TKT-1056  | 2024-09-25 | Late Delivery   | Resolved |\\n| TKT-1057  | 2024-11-11 | Damaged Item    | Open     |"
        result = update_file("user.md", old, new)
    """

    reasoning: str = Field(
        description="Why do you need update file? (1-2 sentences MAX)",
        max_length=200
    )
    file_path: str = Field(description="The path to the file.")
    old_content: str = Field(description="The exact text to find and replace in the file.")
    new_content: str = Field(description="The text to replace old_content with.")

    async def __call__(self, context: ResearchContext, config=None, **kwargs) -> str:
        """
        Выполняем обновление файла, заменяя старый текст на новый для модификации данных.

        Args:
            context: Контекст исследования агента
            config: Конфигурация агента (опционально)
            **kwargs: Дополнительные параметры

        Returns:
            Строка с результатом операции
        """
        final_path = os.path.join(MEMORY_PATH, self.file_path)
        try:
            if not os.path.exists(final_path):
                return f"Error: File '{final_path}' does not exist"

            if not os.path.isfile(final_path):
                return f"Error: '{final_path}' is not a file"

            with open(final_path, "r") as f:
                current_content = f.read()

            if self.old_content not in current_content:
                preview_length = 50
                preview = self.old_content[:preview_length] + "..." if len(self.old_content) > preview_length else self.old_content
                return f"Error: Could not find the specified content in the file. Looking for: '{preview}'"

            occurrences = current_content.count(self.old_content)
            if occurrences > 1:
                return f"Warning: Found {occurrences} occurrences of the content. Replacing only the first one."

            updated_content = current_content.replace(self.old_content, self.new_content, 1)

            if updated_content == current_content:
                return "Error: No changes were made to the file"

            with open(final_path, "w") as f:
                f.write(updated_content)

            return "True"

        except PermissionError:
            return f"Error: Permission denied writing to '{final_path}'"
        except Exception as e:
            return f"Error: Unexpected error - {str(e)}"

