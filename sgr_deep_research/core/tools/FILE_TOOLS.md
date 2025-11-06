# File System Tools for SGRFileAgent

Набор инструментов для поиска и анализа файлов в файловой системе.

## Основные принципы

- **Reasoning-first**: каждый тул требует объяснения (первое поле `reasoning`)
- **Двухфазный режим**: агент сначала рассуждает (reasoning phase), затем выполняет действие (action phase)
- **Read-only**: все операции только для чтения и анализа

## Доступные инструменты

### 1. ReadFileTool
**Назначение**: Чтение содержимого файлов

**Параметры**:
- `reasoning`: Зачем читать файл
- `file_path`: Путь к файлу (абсолютный или относительный)
- `start_line`: Начальная строка (опционально, 1-based)
- `end_line`: Конечная строка (опционально, 1-based)

**Примеры использования**:
```python
# Прочитать весь файл
ReadFileTool(
    reasoning="Нужно изучить конфигурацию проекта",
    file_path="config.yaml"
)

# Прочитать определенные строки
ReadFileTool(
    reasoning="Проверить импорты в начале файла",
    file_path="main.py",
    start_line=1,
    end_line=20
)
```

### 2. ListDirectoryTool
**Назначение**: Просмотр содержимого директорий

**Параметры**:
- `reasoning`: Зачем просматривать директорию
- `directory_path`: Путь к директории
- `recursive`: Рекурсивный просмотр (по умолчанию False)

**Примеры использования**:
```python
# Посмотреть содержимое директории
ListDirectoryTool(
    reasoning="Изучить структуру проекта",
    directory_path="./src",
    recursive=False
)

# Рекурсивный просмотр
ListDirectoryTool(
    reasoning="Получить полную структуру проекта",
    directory_path=".",
    recursive=True
)
```

### 3. SearchFilesTool
**Назначение**: Поиск файлов по имени/паттерну

**Параметры**:
- `reasoning`: Зачем искать файлы
- `pattern`: Паттерн поиска (например, `*.py`, `config.*`, `test_*`)
- `directory`: Директория для поиска (по умолчанию ".")
- `recursive`: Рекурсивный поиск (по умолчанию True)

**Примеры использования**:
```python
# Найти все Python файлы
SearchFilesTool(
    reasoning="Нужно найти все исходники Python",
    pattern="*.py",
    directory=".",
    recursive=True
)

# Найти конфигурационные файлы
SearchFilesTool(
    reasoning="Найти все конфиги в корне проекта",
    pattern="config.*",
    directory=".",
    recursive=False
)
```

### 4. SearchInFilesTool
**Назначение**: Поиск текста внутри файлов (grep-подобный)

**Параметры**:
- `reasoning`: Зачем искать текст
- `search_text`: Текст или regex для поиска
- `directory`: Директория для поиска (по умолчанию ".")
- `file_pattern`: Паттерн файлов (по умолчанию "*")
- `case_sensitive`: Чувствительность к регистру (по умолчанию True)
- `regex`: Использовать regex (по умолчанию False)
- `max_results`: Максимум результатов (по умолчанию 50)

**Примеры использования**:
```python
# Найти все использования класса
SearchInFilesTool(
    reasoning="Найти где используется BaseTool",
    search_text="BaseTool",
    directory="./sgr_deep_research",
    file_pattern="*.py",
    case_sensitive=True
)

# Поиск с regex
SearchInFilesTool(
    reasoning="Найти все функции async def",
    search_text="async def \\w+",
    directory=".",
    file_pattern="*.py",
    regex=True
)
```

### 5. FindByExtensionTool
**Назначение**: Поиск файлов по расширению

**Параметры**:
- `reasoning`: Зачем искать файлы по расширению
- `directory`: Директория для поиска (по умолчанию ".")
- `extensions`: Список расширений (например, ['py', 'js', 'ts'])
- `recursive`: Рекурсивный поиск (по умолчанию True)
- `group_by_extension`: Группировать по расширению (по умолчанию False)

**Примеры использования**:
```python
# Найти все Python файлы
FindByExtensionTool(
    reasoning="Найти все исходники Python",
    directory=".",
    extensions=["py"],
    recursive=True
)

# Найти конфигурационные файлы разных типов
FindByExtensionTool(
    reasoning="Найти все конфиги проекта",
    directory=".",
    extensions=["yaml", "json", "toml", "ini"],
    group_by_extension=True
)

# Найти документацию
FindByExtensionTool(
    reasoning="Найти всю документацию",
    directory="./docs",
    extensions=["md", "txt", "rst"]
)
```

### 6. FindBySizeTool
**Назначение**: Поиск файлов по размеру

**Параметры**:
- `reasoning`: Зачем искать файлы по размеру
- `directory`: Директория для поиска (по умолчанию ".")
- `min_size_bytes`: Минимальный размер в байтах (опционально)
- `max_size_bytes`: Максимальный размер в байтах (опционально)
- `recursive`: Рекурсивный поиск (по умолчанию True)

**Примеры использования**:
```python
# Найти большие файлы (>1MB)
FindBySizeTool(
    reasoning="Найти файлы которые занимают много места",
    directory=".",
    min_size_bytes=1024 * 1024,  # 1MB
    recursive=True
)

# Найти маленькие файлы (<1KB)
FindBySizeTool(
    reasoning="Найти возможно пустые или очень маленькие файлы",
    directory=".",
    max_size_bytes=1024,  # 1KB
    recursive=True
)

# Найти файлы в диапазоне (100KB - 500KB)
FindBySizeTool(
    reasoning="Найти файлы среднего размера",
    directory=".",
    min_size_bytes=100 * 1024,  # 100KB
    max_size_bytes=500 * 1024,  # 500KB
    recursive=True
)
```

### 7. FindByDateTool
**Назначение**: Поиск файлов по дате модификации

**Параметры**:
- `reasoning`: Зачем искать файлы по дате
- `directory`: Директория для поиска (по умолчанию ".")
- `days_ago`: Найти файлы измененные за последние N дней (опционально)
- `older_than_days`: Найти файлы старше N дней (опционально)
- `recursive`: Рекурсивный поиск (по умолчанию True)

**Примеры использования**:
```python
# Найти недавно измененные файлы (последние 7 дней)
FindByDateTool(
    reasoning="Найти файлы над которыми работали на этой неделе",
    directory=".",
    days_ago=7,
    recursive=True
)

# Найти старые файлы (старше 365 дней)
FindByDateTool(
    reasoning="Найти файлы которые давно не обновлялись",
    directory=".",
    older_than_days=365,
    recursive=True
)

# Найти файлы измененные сегодня
FindByDateTool(
    reasoning="Показать что изменилось сегодня",
    directory=".",
    days_ago=1,
    recursive=True
)
```

## Комбинирование инструментов

Агент может комбинировать несколько инструментов для решения сложных задач:

**Пример задачи**: "Найди все большие Python файлы (>100KB), измененные за последнюю неделю, и покажи их содержимое"

Агент выполнит:
1. `FindByExtensionTool` - найдет все .py файлы
2. `FindBySizeTool` - отфильтрует файлы >100KB
3. `FindByDateTool` - оставит только измененные за неделю
4. `ReadFileTool` - прочитает содержимое найденных файлов

## Архитектура

```
SGRFileAgent
├── Reasoning Phase: анализ задачи, планирование
└── Action Phase: выполнение инструмента
    ├── System Tools
    │   ├── ClarificationTool
    │   ├── ReasoningTool
    │   └── FinalAnswerTool
    └── File System Tools
        ├── ReadFileTool
        ├── ListDirectoryTool
        ├── SearchFilesTool
        ├── SearchInFilesTool
        ├── FindByExtensionTool
        ├── FindBySizeTool
        └── FindByDateTool
```

## Размеры файлов (справка)

- 1 KB = 1,024 bytes
- 1 MB = 1,048,576 bytes (1024 * 1024)
- 1 GB = 1,073,741,824 bytes (1024 * 1024 * 1024)

## Паттерны поиска (справка)

- `*.py` - все Python файлы
- `test_*.py` - все тестовые файлы
- `config.*` - файлы config с любым расширением
- `*.{yaml,yml}` - YAML файлы с разными расширениями
- `__init__.py` - точное имя файла
