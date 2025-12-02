"""
Инструмент для создания файлов в памяти агента.

Создает новый файл с заданным содержимым, проверяя соблюдение лимитов размеров.
"""

import os
import uuid

from pydantic import Field

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.models import ResearchContext
from sgr_deep_research.core.tools.mem_tools.settings import MEMORY_PATH
from sgr_deep_research.core.tools.mem_tools.utils import check_size_limits


class CreateFileTool(BaseTool):
    """
    Создаем новый файл в памяти с указанным содержимым, чтобы сохранить данные агента.

    Сначала создаем временный файл с заданным содержимым, проверяем соблюдение лимитов размеров,
    и если все в порядке, перемещаем временный файл в финальное местоположение.

    Args:
        reasoning: Обоснование необходимости создания файла (1-2 предложения)
        file_path: Путь к создаваемому файлу
        content: Содержимое файла

    Returns:
        "True" если файл создан успешно, иначе сообщение об ошибке
    """

    reasoning: str = Field(
        description="Why do you need create file? (1-2 sentences MAX)",
        max_length=200
    )
    file_path: str = Field(description="The path to the file.")
    content: str = Field(description="The content of the file.")

    async def __call__(self, context: ResearchContext, config=None, **kwargs) -> str:
        """
        Выполняем создание файла, проверяя лимиты размеров для безопасности.

        Args:
            context: Контекст исследования агента
            config: Конфигурация агента (опционально)
            **kwargs: Дополнительные параметры

        Returns:
            Строка с результатом операции
        """
        final_path = os.path.join(MEMORY_PATH, self.file_path)
        temp_file_path = None
        try:
            parent_dir = os.path.dirname(final_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)

            target_dir = os.path.dirname(os.path.abspath(final_path)) or "."
            temp_file_path = os.path.join(target_dir, f"temp_{uuid.uuid4().hex[:8]}.txt")

            with open(temp_file_path, "w") as f:
                f.write(self.content)

            if check_size_limits(temp_file_path):
                with open(final_path, "w") as f:
                    f.write(self.content)
                os.remove(temp_file_path)
                return "True"
            else:
                os.remove(temp_file_path)
                raise Exception(f"File {final_path} is too large to create")
        except Exception as e:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except Exception as cleanup_error:
                    raise Exception(f"Error removing temp file {temp_file_path}: {cleanup_error}")
            raise Exception(f"Error creating file {final_path}: {e}")

