"""
Вспомогательные функции для проверки размеров файлов и директорий.

Содержит функции для контроля за соблюдением лимитов размеров при работе с файловой системой.
"""

import os

from sgr_deep_research.core.tools.mem_tools.settings import (
    DIR_SIZE_LIMIT,
    FILE_SIZE_LIMIT,
    MEMORY_SIZE_LIMIT,
)


def check_file_size_limit(file_path: str) -> bool:
    """
    Проверяем размер файла на соответствие лимиту, чтобы контролировать использование памяти.

    Args:
        file_path: Путь к файлу для проверки

    Returns:
        True если размер файла не превышает лимит, False иначе
    """
    return os.path.getsize(file_path) <= FILE_SIZE_LIMIT


def check_dir_size_limit(dir_path: str) -> bool:
    """
    Проверяем размер директории на соответствие лимиту, чтобы контролировать использование памяти.

    Args:
        dir_path: Путь к директории для проверки

    Returns:
        True если размер директории не превышает лимит, False иначе
    """
    return os.path.getsize(dir_path) <= DIR_SIZE_LIMIT


def check_memory_size_limit() -> bool:
    """
    Проверяем общий размер памяти на соответствие лимиту, чтобы предотвратить переполнение.

    Returns:
        True если общий размер не превышает лимит, False иначе
    """
    current_working_dir = os.getcwd()
    return os.path.getsize(current_working_dir) <= MEMORY_SIZE_LIMIT


def check_size_limits(file_or_dir_path: str) -> bool:
    """
    Проверяем все применимые лимиты размеров для заданного пути, чтобы обеспечить безопасность операции.

    Args:
        file_or_dir_path: Путь к файлу или директории для проверки

    Returns:
        True если все лимиты соблюдены, False иначе
    """
    if file_or_dir_path == "":
        return check_memory_size_limit()
    elif os.path.isdir(file_or_dir_path):
        return check_dir_size_limit(file_or_dir_path) and check_memory_size_limit()
    elif os.path.isfile(file_or_dir_path):
        parent_dir = os.path.dirname(file_or_dir_path)
        if not parent_dir == "":
            return (
                check_file_size_limit(file_or_dir_path)
                and check_dir_size_limit(parent_dir)
                and check_memory_size_limit()
            )
        else:
            return check_file_size_limit(file_or_dir_path) and check_memory_size_limit()
    else:
        return False

