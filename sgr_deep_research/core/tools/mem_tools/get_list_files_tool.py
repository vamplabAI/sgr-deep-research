"""
Инструмент для получения списка файлов и директорий в памяти агента.

Отображает структуру директорий в виде дерева.
"""

import os

from pydantic import Field

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.models import ResearchContext
from sgr_deep_research.core.tools.mem_tools.settings import MEMORY_PATH


class GetListFilesTool(BaseTool):
    """
    Отображаем все файлы и директории в виде древовидной структуры, чтобы показать организацию данных.

    Пример вывода:
    ```
    ./
    ├── user.md
    └── entities/
        ├── 452_willow_creek_dr.md
        └── frank_miller_plumbing.md
    ```

    Args:
        reasoning: Обоснование необходимости получения списка (1-2 предложения)

    Returns:
        Строковое представление дерева директорий
    """

    reasoning: str = Field(
        description="Why do you need get files list? (1-2 sentences MAX)",
        max_length=200
    )

    async def __call__(self, context: ResearchContext, config=None, **kwargs) -> str:
        """
        Выполняем построение дерева файлов, рекурсивно обходя директории для полного отображения.

        Args:
            context: Контекст исследования агента
            config: Конфигурация агента (опционально)
            **kwargs: Дополнительные параметры

        Returns:
            Строка с древовидной структурой или описание ошибки
        """
        try:
            dir_path = MEMORY_PATH

            def build_tree(start_path: str, prefix: str = "", is_last: bool = True) -> str:
                """
                Рекурсивно строим дерево директорий, чтобы визуализировать структуру файлов.

                Args:
                    start_path: Начальный путь для построения дерева
                    prefix: Префикс для отступов
                    is_last: Является ли элемент последним в списке

                Returns:
                    Строковое представление дерева
                """
                entries = []
                try:
                    items = sorted(os.listdir(start_path))
                    items = [item for item in items if not item.startswith('.') and item != '__pycache__']
                except PermissionError:
                    return f"{prefix}[Permission Denied]\n"

                if not items:
                    return ""

                for i, item in enumerate(items):
                    item_path = os.path.join(start_path, item)
                    is_last_item = i == len(items) - 1

                    if is_last_item:
                        current_prefix = prefix + "└── "
                        extension = prefix + "    "
                    else:
                        current_prefix = prefix + "├── "
                        extension = prefix + "│   "

                    if os.path.isdir(item_path):
                        try:
                            dir_contents = [f for f in os.listdir(item_path)
                                          if not f.startswith('.') and f != '__pycache__']
                            if not dir_contents:
                                entries.append(f"{current_prefix}{item}/ (empty)\n")
                            else:
                                entries.append(f"{current_prefix}{item}/\n")
                                entries.append(build_tree(item_path, extension, is_last_item))
                        except PermissionError:
                            entries.append(f"{current_prefix}{item}/ [Permission Denied]\n")
                    else:
                        entries.append(f"{current_prefix}{item}\n")

                return "".join(entries)

            tree = f"./\n{build_tree(dir_path)}"
            return tree.rstrip()

        except Exception as e:
            return f"Error: {e}"

