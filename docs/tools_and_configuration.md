# SGR Deep Research - Tools & Configuration Guide

## Содержание
1. [Обзор архитектуры](#обзор-архитектуры)
2. [Инструменты (Tools)](#инструменты-tools)
3. [Конфигурация системы](#конфигурация-системы)
4. [Агенты](#агенты)
5. [Примеры использования](#примеры-использования)

---

## Обзор архитектуры

SGR Deep Research использует модульную архитектуру с тремя основными компонентами:
- **Agents** - исследовательские агенты с различными стратегиями работы
- **Tools** - инструменты для поиска, создания отчетов и управления процессом
- **Configuration** - гибкая система настроек через YAML

### Workflow агента

```
1. Reasoning Phase    → Анализ ситуации и планирование
2. Select Action      → Выбор подходящего инструмента
3. Action Phase       → Выполнение действия с помощью инструмента
4. Update Context     → Обновление контекста и переход к следующей итерации
```

---

## Инструменты (Tools)

Все инструменты наследуются от базового класса `BaseTool` и делятся на две категории:

### System Tools (Системные инструменты)

Базовые инструменты для управления процессом исследования.

#### 1. ReasoningTool
**Назначение:** Ядро агента - анализирует текущую ситуацию и планирует следующие шаги.

**Поля:**
- `reasoning_steps` (list[str], 2-4 шага) - Пошаговый процесс рассуждения
- `current_situation` (str) - Анализ текущей ситуации исследования
- `plan_status` (str) - Статус выполнения плана
- `enough_data` (bool) - Достаточно ли данных для создания отчета
- `remaining_steps` (list[str], 1-3 шага) - Оставшиеся шаги для завершения задачи
- `task_completed` (bool) - Завершена ли задача исследования

**Когда используется:**
- В начале каждой итерации (кроме `sgr_agent`)
- Для адаптивного планирования исследования
- Оценки прогресса и необходимости дополнительных действий

**Пример:**
```json
{
  "reasoning_steps": [
    "Пользователь запросил информацию о цене биткоина",
    "Нужно выполнить поиск актуальной информации",
    "После получения данных - создать отчет"
  ],
  "current_situation": "Начало исследования, данных пока нет",
  "plan_status": "Not started",
  "enough_data": false,
  "remaining_steps": [
    "Найти текущую цену биткоина",
    "Создать отчет с полученными данными"
  ],
  "task_completed": false
}
```

---

#### 2. ClarificationTool
**Назначение:** Запрашивает уточнения у пользователя при неоднозначных или неполных запросах.

**Поля:**
- `reasoning` (str) - Почему требуется уточнение
- `unclear_terms` (list[str], 1-5 терминов) - Список неясных терминов или концепций
- `assumptions` (list[str], 2-4 предположения) - Возможные интерпретации для проверки
- `questions` (list[str], 3-5 вопросов) - Конкретные уточняющие вопросы

**Когда используется:**
- Запрос слишком неясный или двусмысленный
- Отсутствуют критически важные детали
- Нужно уточнить направление исследования

**Ограничения:**
- Максимум `max_clarifications` раз за сеанс (по умолчанию 3)
- После достижения лимита инструмент недоступен

**Пример:**
```json
{
  "reasoning": "Запрос 'ку' недостаточно конкретен для исследования",
  "unclear_terms": ["ку"],
  "assumptions": [
    "Возможно, опечатка или сокращение",
    "Может быть название компании/продукта",
    "Возможно, пользователь хочет задать другой вопрос"
  ],
  "questions": [
    "Что именно вы хотите узнать?",
    "Уточните, пожалуйста, тему исследования",
    "Возможно, это опечатка? Какую информацию вы ищете?"
  ]
}
```

---

#### 3. GeneratePlanTool
**Назначение:** Создает структурированный план исследования для сложных задач.

**Поля:**
- `reasoning` (str) - Обоснование подхода к исследованию
- `research_goal` (str) - Основная цель исследования
- `planned_steps` (list[str], 3-4 шага) - Список запланированных шагов
- `search_strategies` (list[str], 2-3 стратегии) - Стратегии поиска информации

**Когда используется:**
- В начале сложного многошагового исследования
- Для структурирования большой задачи

**Пример:**
```json
{
  "reasoning": "Сложный запрос требует поэтапного подхода",
  "research_goal": "Провести анализ рынка криптовалют за 2025 год",
  "planned_steps": [
    "Собрать данные о текущих ценах основных криптовалют",
    "Найти аналитические отчеты за последний квартал",
    "Проанализировать тенденции и прогнозы",
    "Синтезировать выводы в итоговом отчете"
  ],
  "search_strategies": [
    "Поиск актуальных биржевых данных",
    "Анализ отчетов ведущих аналитиков",
    "Изучение новостей и событий рынка"
  ]
}
```

---

#### 4. AdaptPlanTool
**Назначение:** Адаптирует план исследования на основе новых данных или изменившихся обстоятельств.

**Поля:**
- `reasoning` (str) - Почему план нуждается в адаптации
- `original_goal` (str) - Исходная цель исследования
- `new_goal` (str) - Обновленная цель исследования
- `plan_changes` (list[str], 1-3 изменения) - Конкретные изменения в плане
- `next_steps` (list[str], 2-4 шага) - Обновленные оставшиеся шаги

**Когда используется:**
- Найдена информация, противоречащая начальным предположениям
- Обнаружены новые аспекты проблемы
- Исходный план оказался неэффективным

**Пример:**
```json
{
  "reasoning": "Обнаружено, что биржа Binance приостановила торги BTC",
  "original_goal": "Найти цену биткоина на бирже Binance",
  "new_goal": "Найти актуальную цену биткоина на альтернативных биржах",
  "plan_changes": [
    "Изменен источник данных с Binance на Coinbase и Kraken",
    "Добавлена информация о причинах приостановки торгов"
  ],
  "next_steps": [
    "Получить данные с альтернативных бирж",
    "Сравнить цены на разных площадках",
    "Создать отчет с учетом новых обстоятельств"
  ]
}
```

---

#### 5. AgentCompletionTool
**Назначение:** Финализирует задачу исследования и завершает работу агента.

**Поля:**
- `reasoning` (str) - Почему задача считается завершенной
- `completed_steps` (list[str], 1-5 шагов) - Резюме выполненных шагов
- `status` (Literal["completed", "failed"]) - Статус завершения задачи

**Когда используется:**
- Все шаги исследования выполнены
- Достигнут лимит итераций
- Произошла критическая ошибка (status="failed")

**Эффект:**
- Устанавливает `context.state = status`
- Завершает цикл выполнения агента
- Сохраняет лог выполнения

**Пример:**
```json
{
  "reasoning": "Получена актуальная цена биткоина, отчет создан",
  "completed_steps": [
    "Выполнен поиск текущей цены BTC",
    "Получены данные с 5 источников",
    "Создан детализированный отчет с цитированием"
  ],
  "status": "completed"
}
```

---

### Research Tools (Инструменты исследования)

Специализированные инструменты для поиска и обработки информации.

#### 1. WebSearchTool
**Назначение:** Выполняет веб-поиск через Tavily API для сбора информации.

**Поля:**
- `reasoning` (str) - Зачем нужен поиск и что ожидается найти
- `query` (str) - Поисковый запрос на том же языке, что и запрос пользователя
- `max_results` (int, 1-10, default=10) - Максимальное количество результатов
- `scrape_content` (bool, default=False) - Загружать ли полный контент страниц

**Рекомендации:**
- Используйте КОНКРЕТНЫЕ термины и контекст в запросах
- Для аббревиатур добавляйте контекст: "SGR Schema-Guided Reasoning"
- Используйте кавычки для точных фраз: "Structured Output OpenAI"
- Поисковые запросы НА ТОМ ЖЕ ЯЗЫКЕ, что и запрос пользователя
- `scrape_content=True` для более глубокого анализа (загружает полный контент страницы)

**Ограничения:**
- Максимум `max_searches` раз за сеанс (по умолчанию 4)
- После достижения лимита инструмент недоступен
- Контент ограничен `config.scraping.content_limit` символами

**Эффект:**
- Добавляет найденные источники в `context.sources`
- Увеличивает `context.searches_used`
- Сохраняет результат в `context.searches`

**Пример:**
```json
{
  "reasoning": "Нужна актуальная цена биткоина на сегодня",
  "query": "текущая цена биткоина сентябрь 2025",
  "max_results": 5,
  "scrape_content": false
}
```

**Результат:**
```
Search Query: текущая цена биткоина сентябрь 2025

Search Results:

[1] Bitcoin Price Today - CoinMarketCap - https://coinmarketcap.com/...
Bitcoin is currently trading at $63,245.50 USD...

[2] BTC/USD - Binance - https://binance.com/...
Real-time Bitcoin price: $63,240.12...
```

---

#### 2. CreateReportTool
**Назначение:** Создает итоговый детализированный отчет с цитированием источников.

**Поля:**
- `reasoning` (str) - Почему готов создать отчет сейчас
- `title` (str) - Заголовок отчета
- `user_request_language_reference` (str) - Копия исходного запроса пользователя для соблюдения языка
- `content` (str) - Полное содержание отчета (следует REPORT CREATION GUIDELINES)
- `confidence` (Literal["high", "medium", "low"]) - Уровень уверенности в выводах

**Требования к отчету:**

**Структура (4 раздела):**
1. **Executive Summary** - ключевые выводы с метриками и уровнями уверенности
2. **Technical Analysis** - многомерное исследование с использованием ВСЕХ источников
3. **Key Findings** - выводы на основе доказательств, ранжированные по уверенности
4. **Conclusions** - итоговый синтез с практическими рекомендациями

**Обязательные требования:**
- Каждое утверждение ДОЛЖНО иметь встроенные цитаты [1], [2], [3]
- Использовать ВСЕ доступные источники из исследования
- Включать конкретные числа и метрики, не расплывчатые определения
- Перекрестная ссылка на противоречивую информацию: "Источник A утверждает X [1], в то время как источник B предполагает Y [2]"
- Применять критическое мышление и оценку достоверности источников
- Явно признавать ограничения исследования и неопределенность
- Демонстрировать оригинальный аналитический синтез, а не просто суммирование

**Эффект:**
- Сохраняет отчет в `config.execution.reports_dir`
- Имя файла: `YYYYMMDD_HHMMSS_<safe_title>.md`
- Включает метаданные: timestamp, source count, word count

**Пример запроса:**
```json
{
  "reasoning": "Собрано 5 актуальных источников о цене биткоина",
  "title": "Текущая цена биткоина",
  "user_request_language_reference": "Найди цену биткоина",
  "content": "# Executive Summary\n\nБиткоин торгуется на уровне $63,245 [1]...",
  "confidence": "high"
}
```

**Пример цитирования:**
- Русский: "Исследование показывает рост на 47.3% [1], что подтверждается данными [2]"
- English: "Research demonstrates 47.3% improvement [1], confirmed by data [2]"

---

### Confluence Tools (Инструменты для корпоративной базы знаний)

Специализированные инструменты для поиска информации в корпоративном Confluence.

#### 1. ConfluenceSearchTool
**Назначение:** Поиск информации во внутренней базе знаний Confluence.

**Поля:**
- `reasoning` (str) - Зачем ищем в Confluence и что ожидается найти
- `query` (str) - Поисковый запрос на том же языке, что и запрос пользователя
- `max_results` (int, 1-25, default=10) - Максимальное количество результатов
- `content_type` (Literal["page", "blogpost", "attachment"], default="page") - Тип контента для поиска
- `include_content` (bool, default=False) - Включать ли полный текст страниц

**Когда использовать:**
- Нужна внутренняя документация компании
- Поиск технических гайдов, архитектурных решений
- Информация о проектах, процессах, политиках
- Внутренние знания, недоступные в интернете

**Рекомендации:**
- Используйте конкретные технические термины и названия проектов
- Поисковые запросы НА ТОМ ЖЕ ЯЗЫКЕ, что и запрос пользователя
- Для русских запросов: "архитектура SmartPlatform"
- Для английских запросов: "SmartPlatform architecture"
- `include_content=True` для глубокого анализа (загружает полный текст)

**Эффект:**
- Возвращает список найденных страниц с метаданными
- Если `include_content=True`, включает полный текст страниц

**Пример:**
```json
{
  "reasoning": "Нужна информация о развертывании SmartPlatform",
  "query": "развертывание SmartPlatform инструкция",
  "max_results": 10,
  "content_type": "page",
  "include_content": false
}
```

**Результат:**
```
Confluence Search Query: развертывание SmartPlatform инструкция
Total Found: 15 items
Showing: 10 results

Results:

[1] Инструкция по развертыванию SmartPlatform для 2х серверов
    Type: page
    Space: NDT Smart Platform (NDTALL)
    URL: https://conf.redmadrobot.com/pages/viewpage.action?pageId=4266431153
    Version: 3
    Updated: 2025-08-15T14:32:00Z by Иванов И.И.

[2] Постановка на разработку Smart Platform
    Type: page
    Space: NDT Smart Platform (NDTALL)
    URL: https://conf.redmadrobot.com/pages/viewpage.action?pageId=123456789
    Version: 5
    Updated: 2025-09-01T09:15:00Z by Петров П.П.
```

---

#### 2. ConfluenceSpaceSearchTool
**Назначение:** Поиск внутри конкретного пространства (space) Confluence для более точных результатов.

**Поля:**
- `reasoning` (str) - Почему ищем именно в этом пространстве
- `query` (str) - Поисковый запрос на том же языке, что и запрос пользователя
- `space_key` (str) - Ключ пространства Confluence (например, 'NDTALL', 'NH', 'BAN')
- `max_results` (int, 1-25, default=10) - Максимальное количество результатов
- `include_content` (bool, default=False) - Включать ли полный текст страниц

**Когда использовать:**
- Известно конкретное пространство (проект/команда)
- Нужна более целенаправленная информация
- Избежать результатов из других проектов

**Популярные пространства:**
- `NDTALL` - Документация NDT Smart Platform
- `NH` - Общая проектная документация
- `BAN` - Банковские проекты
- `GPP` - Проектные комитеты

**Эффект:**
- Ограничивает поиск конкретным пространством
- Более релевантные результаты для специфичных проектов

**Пример:**
```json
{
  "reasoning": "Ищем техническую документацию именно по Smart Platform",
  "query": "API интеграция",
  "space_key": "NDTALL",
  "max_results": 10,
  "include_content": false
}
```

**Результат:**
```
Confluence Space Search
Query: API интеграция
Space: NDTALL
Total Found: 8 pages
Showing: 8 results

Results:

[1] API SmartPlatform - Руководство разработчика
    Page ID: 4266429015
    URL: https://conf.redmadrobot.com/pages/viewpage.action?pageId=4266429015
    Version: 12
    Updated: 2025-09-20T16:45:00Z by Сидоров С.С.
```

---

#### 3. ConfluencePageTool
**Назначение:** Получить полный контент конкретной страницы Confluence по ID.

**Поля:**
- `reasoning` (str) - Почему загружаем именно эту страницу
- `page_id` (str) - ID страницы Confluence (например, '123456789')

**Когда использовать:**
- Найдена нужная страница в результатах поиска
- Нужен полный текст, а не только превью
- Глубокий анализ конкретного документа

**Как получить page_id:**
- Из результатов `ConfluenceSearchTool` или `ConfluenceSpaceSearchTool`
- Из URL страницы (параметр `pageId`)
- Из прямой ссылки в Confluence

**Эффект:**
- Загружает полный текст страницы
- Включает все метаданные (версия, автор, дата)
- Конвертирует HTML в читаемый текст

**Пример:**
```json
{
  "reasoning": "Нужен полный текст инструкции по развертыванию",
  "page_id": "4266431153"
}
```

**Результат:**
```
Confluence Page
================================================================================

Title: Инструкция по развертыванию SmartPlatform для 2х серверов
ID: 4266431153
Type: page
Space: NDT Smart Platform (NDTALL)
URL: https://conf.redmadrobot.com/pages/viewpage.action?pageId=4266431153
Version: 3
Last Updated: 2025-08-15T14:32:00Z by Иванов И.И.

================================================================================

Content:

# Требования к инфраструктуре

Для развертывания SmartPlatform необходимо:

1. Два сервера с характеристиками:
   - CPU: 8 cores
   - RAM: 32 GB
   - Storage: 500 GB SSD

2. Операционная система: Ubuntu 22.04 LTS

3. Установленное ПО:
   - Docker 24.0+
   - Docker Compose 2.20+
   - PostgreSQL 15+

...
```

---

**Коллекция Confluence Tools:**
```python
confluence_agent_tools = [
    ConfluenceSearchTool,
    ConfluenceSpaceSearchTool,
    ConfluencePageTool,
]
```

---

## Конфигурация системы

Настройки хранятся в файле `config.yaml` (создается из `config.yaml.example`).

### OpenAI Configuration

```yaml
openai:
  api_key: "your-openai-api-key-here"  # ОБЯЗАТЕЛЬНО: Ваш API ключ OpenAI
  base_url: ""                         # ОПЦИОНАЛЬНО: Альтернативный URL (для proxy LiteLLM/vLLM)
  model: "gpt-4o-mini"                 # Модель для использования
  max_tokens: 8000                     # Максимальное количество токенов
  temperature: 0.4                     # Температура генерации (0.0-1.0)
  proxy: ""                            # Прокси: "socks5://127.0.0.1:1081" или ""
```

**Параметры:**
- `api_key` - API ключ OpenAI (обязательно)
- `base_url` - Базовый URL API. Пустая строка = использовать стандартный OpenAI endpoint
- `model` - Модель LLM для использования. Рекомендуется `gpt-4o-mini` или `gpt-4o`
- `max_tokens` - Максимальная длина ответа модели
- `temperature` - Контролирует случайность (0.0 = детерминированно, 1.0 = креативно)
- `proxy` - HTTP/SOCKS5 прокси для запросов (оставьте пустым если не нужен)

---

### Tavily Search Configuration

```yaml
tavily:
  api_key: "your-tavily-api-key-here"  # ОБЯЗАТЕЛЬНО: Ваш Tavily API ключ
  api_base_url: "https://api.tavily.com"  # Базовый URL Tavily API
```

**Параметры:**
- `api_key` - API ключ Tavily (получите на [tavily.com](https://tavily.com))
- `api_base_url` - Базовый URL Tavily API (обычно не меняется)

**Что делает Tavily:**
- Выполняет веб-поиск по запросам агента
- Возвращает релевантные результаты с URL, заголовками и сниппетами
- Опционально скрапит полный контент страниц
- Обеспечивает свежую информацию из интернета

---

### Confluence Configuration

```yaml
confluence:
  base_url: "https://conf.redmadrobot.com"  # Базовый URL вашего Confluence
  username: "your-username"                  # Имя пользователя
  password: "your-password-or-api-token"     # Пароль или API токен
  timeout: 30.0                              # Таймаут запросов в секундах
```

**Параметры:**
- `base_url` - Базовый URL вашего Confluence сервера
  - Без trailing slash
  - Пример: `https://conf.company.com`
- `username` - Имя пользователя для аутентификации
- `password` - Пароль или API токен
  - Рекомендуется использовать API token вместо пароля
  - Создайте токен в настройках профиля Confluence
- `timeout` (секунды) - Таймаут для HTTP запросов
  - Рекомендуется: 30-60 секунд

**Опциональность:**
- Confluence конфигурация **необязательна**
- Если не указана, Confluence Tools будут недоступны
- Агенты могут работать только с WebSearchTool (Tavily)

**Что делает Confluence интеграция:**
- Поиск во внутренней базе знаний компании
- Доступ к технической документации
- Получение информации о проектах и процессах
- Использование корпоративных знаний для исследований

**Безопасность:**
- Используйте переменные окружения для credentials
- Не коммитьте пароли в репозиторий
- Рекомендуется использовать API tokens вместо паролей
- API токены можно легко отозвать при необходимости

**Получение API токена:**
1. Войдите в Confluence
2. Перейдите в настройки профиля
3. Найдите раздел "Personal Access Tokens" или "API Tokens"
4. Создайте новый токен с правами на чтение
5. Используйте токен в поле `password`

---

### Search Configuration

```yaml
search:
  max_results: 10  # Максимальное количество результатов поиска
```

**Параметры:**
- `max_results` (1-10) - Количество результатов на один поисковый запрос
  - Больше = более полная информация, но дороже и медленнее
  - Меньше = быстрее и дешевле, но может упустить важную информацию
  - Рекомендуется: 5-10 для большинства задач

---

### Scraping Configuration

```yaml
scraping:
  enabled: false       # Включить полное скрапинг текста найденных страниц
  max_pages: 5         # Максимум страниц для скрапинга на один поиск
  content_limit: 1500  # Лимит символов контента на источник
```

**Параметры:**
- `enabled` (bool) - Включает/выключает скрапинг полного контента
  - `false` - Используются только сниппеты из поиска (быстро, дешево)
  - `true` - Загружается полный текст страниц (медленно, но глубже)
- `max_pages` (1-10) - Сколько страниц скрапить из результатов поиска
- `content_limit` (символов) - Максимальная длина контента с одной страницы
  - Защита от перегрузки контекста LLM
  - Рекомендуется: 1000-2000 для gpt-4o-mini

**Когда включать scraping:**
- Нужен глубокий анализ конкретных страниц
- Сниппетов недостаточно для ответа
- Исследование технических документов

**Когда выключать:**
- Быстрые фактоидные запросы
- Ограниченный бюджет токенов
- Нужна скорость работы

---

### Execution Configuration

```yaml
execution:
  max_steps: 6           # Максимум шагов выполнения
  reports_dir: "reports" # Директория для сохранения отчетов
  logs_dir: "logs"       # Директория для сохранения логов
```

**Параметры:**
- `max_steps` (1+) - Максимальное количество итераций агента
  - Защита от бесконечных циклов
  - При достижении лимита агент принудительно завершается
  - Рекомендуется: 6-10 для большинства задач
- `reports_dir` - Куда сохранять готовые отчеты (.md файлы)
- `logs_dir` - Куда сохранять подробные логи выполнения (.json файлы)

---

### Prompts Configuration

```yaml
prompts:
  prompts_dir: "prompts"              # Директория с промптами
  system_prompt_file: "system_prompt.txt"  # Файл системного промпта
```

**Параметры:**
- `prompts_dir` - Директория, где хранятся файлы промптов
- `system_prompt_file` - Имя файла с системным промптом агента

**Системный промпт:**
- Определяет поведение и правила агента
- Включает инструкции по созданию отчетов
- Содержит список доступных источников для цитирования
- Динамически обновляется при каждом вызове LLM

---

## Агенты

### Базовая архитектура

Все агенты наследуются от `BaseAgent` и реализуют стандартный цикл:

```python
while state not in FINISH_STATES:
    iteration += 1
    reasoning = await _reasoning_phase()      # Анализ и планирование
    action_tool = await _select_action_phase(reasoning)  # Выбор инструмента
    result = await _action_phase(action_tool)  # Выполнение действия
    
    if isinstance(action_tool, ClarificationTool):
        await wait_for_user_input()  # Ждем ответа пользователя
```

### Контекст исследования (ResearchContext)

Все агенты работают с единым контекстом:

```python
class ResearchContext:
    state: AgentStatesEnum              # Текущее состояние агента
    iteration: int                      # Номер текущей итерации
    searches: list[SearchResult]        # История поисковых запросов
    sources: dict[str, SourceData]      # Собранные источники (URL -> Source)
    searches_used: int                  # Количество использованных поисков
    clarifications_used: int            # Количество запрошенных уточнений
    current_step_reasoning: ReasoningTool  # Текущее рассуждение агента
```

---

### 1. SGR Agent (`sgr_agent`)

**Основной агент с SGR (Schema-Guided Reasoning) фреймворком.**

**Особенности:**
- Использует Structured Output для reasoning
- Стримит JSON reasoning поэтапно через SSE
- **ВСЕГДА запрашивает уточнения** для неясных запросов
- Не завершается `[DONE]` - ждет ответа пользователя

**Параметры инициализации:**
```python
SGRResearchAgent(
    task="Найди цену биткоина",
    toolkit=None,                    # Дополнительные инструменты
    max_clarifications=3,            # Макс. количество уточнений
    max_iterations=10,               # Макс. количество итераций
    max_searches=4                   # Макс. количество поисков
)
```

**Toolkit:**
```python
system_agent_tools = [
    ClarificationTool,
    GeneratePlanTool,
    AdaptPlanTool,
    AgentCompletionTool,
    # ReasoningTool удален - используется своя схема рассуждения
]

research_agent_tools = [
    WebSearchTool,
    CreateReportTool,
]

# Confluence tools are dynamically added if available
# Including: ConfluenceSearchTool, ConfluenceSpaceSearchTool, ConfluencePageTool, ConfluenceVectorSearchTool
```

**Цикл работы:**
1. **Reasoning Phase:**
   - Использует `NextStepTools` (Structured Output)
   - Возвращает рассуждение + выбранный инструмент в одном вызове
   - Динамически строит union доступных инструментов

2. **Select Action Phase:**
   - Инструмент уже выбран в reasoning phase
   - Добавляет tool call в conversation
   - Стримит tool call через SSE

3. **Action Phase:**
   - Выполняет выбранный инструмент
   - Стримит результат пользователю

**Ограничения инструментов:**
```python
if iteration >= max_iterations:
    # Только финальные инструменты
    tools = {CreateReportTool, AgentCompletionTool}

if clarifications_used >= max_clarifications:
    # Убрать ClarificationTool
    tools.remove(ClarificationTool)

if searches_used >= max_searches:
    # Убрать WebSearchTool
    tools.remove(WebSearchTool)
```

**Когда использовать:**
- Глубокие исследовательские задачи
- Нужен полный контроль над процессом
- Важны детали рассуждения агента
- Готовы обрабатывать уточнения

---

### 2. SGR Tool Calling Agent (`sgr_tool_calling_agent`)

**SGR с native OpenAI function calling для выбора инструментов.**

**Особенности:**
- Использует OpenAI tool calling вместо Structured Output
- Стримит `tool_calls` arguments по частям
- Завершается `"finish_reason": "tool_calls"`
- Включает usage статистику
- **Запрашивает уточнения** при необходимости

**Параметры:** Аналогичны `sgr_agent`

**Toolkit:**
```python
system_agent_tools = [
    ClarificationTool,
    GeneratePlanTool,
    AdaptPlanTool,
    AgentCompletionTool,
    ReasoningTool,  # Включен!
]

research_agent_tools = [
    WebSearchTool,
    CreateReportTool,
]

# Confluence tools are dynamically added if available
# Including: ConfluenceSearchTool, ConfluenceSpaceSearchTool, ConfluencePageTool, ConfluenceVectorSearchTool
```

**Цикл работы:**
1. **Reasoning Phase:**
   - Принудительный вызов `ReasoningTool` через `tool_choice`
   - `tool_choice={"type": "function", "function": {"name": "reasoningtool"}}`
   - Стримит аргументы reasoning tool
   - Сохраняет reasoning в conversation как tool call

2. **Select Action Phase:**
   - Отдельный вызов LLM для выбора action tool
   - `tool_choice="required"` - LLM должен выбрать инструмент
   - Стримит аргументы выбранного инструмента

3. **Action Phase:**
   - Выполняет выбранный инструмент
   - Стримит результат

**Отличия от sgr_agent:**
- Раздельные вызовы для reasoning и action (2 LLM calls вместо 1)
- Использует native tool calling протокол OpenAI
- Более детальная статистика (usage tokens)
- Совместим с OpenAI SDK из коробки

**Когда использовать:**
- Нужна совместимость с OpenAI SDK
- Важна детальная статистика токенов
- Предпочитаете native tool calling

---

### 3. SGR Auto Tool Calling Agent (`sgr_auto_tool_calling_agent`)

**Автоматическая версия - агент САМ решает вызывать ли инструменты.**

**Особенности:**
- Наследует от `SGRToolCallingResearchAgent`
- Единственное отличие: `tool_choice="auto"`
- Стримит `tool_calls` arguments по частям
- Завершается `"finish_reason": "stop"`
- **Полностью завершается** - НЕ ждет ответа пользователя
- Может НЕ выполнять clarification (решает сам)

**Параметры:** Аналогичны `sgr_tool_calling_agent`

**Отличия:**
```python
class SGRAutoToolCallingResearchAgent(SGRToolCallingResearchAgent):
    tool_choice: Literal["auto"] = "auto"  # Единственное отличие!
```

**Поведение:**
- LLM **может** выбрать инструмент, **может** просто ответить текстом
- Подходит для сценариев, где агент работает автономно
- Меньше контроля, больше автономности

**Когда использовать:**
- Автономная работа без участия пользователя
- Benchmark и тестирование
- Не требуется гарантированное выполнение уточнений
- Агент сам решает стратегию

**Когда НЕ использовать:**
- Нужны гарантированные уточнения
- Критична предсказуемость поведения
- Требуется ждать ответа пользователя

---

### Сравнительная таблица агентов

| Характеристика | sgr_agent | sgr_tool_calling_agent | sgr_auto_tool_calling_agent |
|---------------|-----------|------------------------|----------------------------|
| **Reasoning** | Structured Output | Native Tool Calling | Native Tool Calling |
| **LLM calls/iteration** | 1 (reasoning+action) | 2 (reasoning, action) | 2 (reasoning, action) |
| **tool_choice** | Structured Output | "required" | "auto" |
| **Уточнения** | Всегда запрашивает | Всегда запрашивает | Может не запросить |
| **Завершение** | Ждет пользователя | Ждет пользователя | Автозавершение |
| **finish_reason** | "stop" | "tool_calls" | "stop" |
| **Usage stats** | ❌ | ✅ | ✅ |
| **Streaming format** | JSON chunks | tool_calls chunks | tool_calls chunks |
| **Использование** | Глубокое исследование | OpenAI совместимость | Автономная работа |

---

## Примеры использования

### Инициализация агента

```python
from sgr_deep_research.core.agents import SGRResearchAgent

agent = SGRResearchAgent(
    task="Найди текущую цену биткоина на бирже Binance",
    max_clarifications=3,
    max_iterations=10,
    max_searches=4
)

# Запуск в фоне
import asyncio
asyncio.create_task(agent.execute())

# Потоковая передача результатов
async for chunk in agent.streaming_generator:
    print(chunk)
```

---

### Предоставление уточнения

```python
# Агент запросил уточнение через ClarificationTool
# Теперь предоставляем ответ

await agent.provide_clarification(
    "Нужна текущая цена на споте, не на фьючерсах"
)

# Агент продолжит работу автоматически
```

---

### Ограничение доступных инструментов

```python
# Агент автоматически ограничивает инструменты на основе прогресса:

# После достижения max_searches=4:
#   WebSearchTool становится недоступен

# После достижения max_clarifications=3:
#   ClarificationTool становится недоступен

# После достижения max_iterations=10:
#   Доступны только CreateReportTool и AgentCompletionTool
```

---

### Проверка состояния

```python
# Текущее состояние
state = agent._context.state
# Возможные значения: inited, researching, waiting_for_clarification, 
#                     completed, error, failed

# Прогресс
print(f"Итерация: {agent._context.iteration}")
print(f"Поисков: {agent._context.searches_used}/{agent.max_searches}")
print(f"Уточнений: {agent._context.clarifications_used}/{agent.max_clarifications}")
print(f"Источников: {len(agent._context.sources)}")

# Текущее рассуждение
reasoning = agent._context.current_step_reasoning
print(f"План: {reasoning.plan_status}")
print(f"Следующие шаги: {reasoning.remaining_steps}")
```

---

### Кастомные инструменты

```python
from sgr_deep_research.core.tools import BaseTool
from pydantic import Field

class CustomDataTool(BaseTool):
    """Fetch data from custom API."""
    
    query: str = Field(description="Query to execute")
    
    def __call__(self, context: ResearchContext) -> str:
        # Ваша логика
        result = fetch_from_api(self.query)
        return json.dumps(result)

# Использование
agent = SGRResearchAgent(
    task="Research custom data",
    toolkit=[CustomDataTool]  # Добавить к стандартным инструментам
)
```

---

### Логирование и отладка

```python
# Агент автоматически логирует все действия
import logging

# Посмотреть подробные логи
logging.basicConfig(level=logging.INFO)

# Логи сохраняются в файл после завершения:
# logs/YYYYMMDD-HHMMSS-{agent_id}-log.json

# Структура лога:
{
  "id": "sgr_agent_47217627-d8e4-4618-8899-bf0c13b0688d",
  "model_config": {
    "model": "gpt-4o-mini",
    "temperature": 0.4,
    ...
  },
  "task": "Найди цену биткоина",
  "log": [
    {
      "step_number": 1,
      "timestamp": "2025-09-29T10:30:45",
      "step_type": "reasoning",
      "agent_reasoning": {...}
    },
    {
      "step_number": 1,
      "timestamp": "2025-09-29T10:30:50",
      "step_type": "tool_execution",
      "tool_name": "websearchtool",
      "agent_tool_context": {...},
      "agent_tool_execution_result": "..."
    }
  ]
}
```

---

## Лучшие практики

### Настройка параметров

**Для быстрых запросов:**
```yaml
execution:
  max_steps: 4
search:
  max_results: 5
scraping:
  enabled: false
```

**Для глубоких исследований:**
```yaml
execution:
  max_steps: 10
search:
  max_results: 10
scraping:
  enabled: true
  max_pages: 5
  content_limit: 2000
```

---

### Оптимизация токенов

1. **Отключите scraping** если достаточно сниппетов
2. **Уменьшите max_results** до 5-7 для простых задач
3. **Снизьте content_limit** до 1000 символов
4. **Используйте gpt-4o-mini** вместо gpt-4o

---

### Обработка ошибок

```python
try:
    await agent.execute()
except Exception as e:
    print(f"Error: {e}")
    # Лог все равно сохранится в logs/
    # Состояние будет FAILED
```

---

### Выбор агента

- **sgr_agent** - если нужен полный контроль и детальное reasoning
- **sgr_tool_calling_agent** - если нужна совместимость с OpenAI SDK
- **sgr_auto_tool_calling_agent** - для автономных benchmark и тестов

---

## Заключение

SGR Deep Research предоставляет гибкую систему для создания исследовательских агентов с адаптивным планированием. Ключевые преимущества:

✅ **Модульная архитектура** - легко расширяемая система инструментов  
✅ **Адаптивное планирование** - агенты корректируют план на основе новых данных  
✅ **Гибкая конфигурация** - все параметры настраиваются через YAML  
✅ **Streaming поддержка** - результаты передаются в реальном времени  
✅ **Детальное логирование** - полная трассировка выполнения  
✅ **OpenAI совместимость** - работает со стандартными SDK и API  

Для начала работы:
1. Скопируйте `config.yaml.example` → `config.yaml`
2. Заполните API ключи (OpenAI и Tavily)
3. Настройте параметры под вашу задачу
4. Выберите подходящего агента
5. Запустите исследование!
