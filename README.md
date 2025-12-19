# SGR Agent Core — the first SGR open-source agentic framework for Schema-Guided Reasoning

## Description

![SGR Concept Architecture](docs/sgr_concept.png)
Open-source agentic framework for building intelligent research agents using Schema-Guided Reasoning. The project provides a core library with a extendable BaseAgent interface implementing a two-phase architecture and multiple ready-to-use research agent implementations built on top of it.

The library includes extensible tools for search, reasoning, and clarification, real-time streaming responses, OpenAI-compatible REST API. Works with any OpenAI-compatible LLM, including local models for fully private research.

______________________________________________________________________

## 🚀 Quick Start: Confluence Research Agent

**Confluence Research Agent** — это специализированный агент для поиска и анализа внутренней документации в Confluence. Агент использует Schema-Guided Reasoning для интеллектуального поиска, анализа и синтеза информации из корпоративной базы знаний.

> 💡 **Хотите запустить за 5 минут?** См. [Quick Start Guide](QUICKSTART_CONFLUENCE.md)

### Возможности

- 🔍 **Полнотекстовый поиск** по всей базе Confluence или в конкретных пространствах
- 📄 **Извлечение контента** страниц с поддержкой пагинации для больших документов
- 🧠 **Интеллектуальный анализ** с использованием Schema-Guided Reasoning
- 💬 **Контекстная память** — агент помнит историю диалога и контекст беседы
- 🔗 **Ссылки на источники** — все ответы содержат прямые ссылки на страницы Confluence
- 🌐 **OpenAI-совместимый API** — легко интегрируется с Open WebUI и другими клиентами

### Установка и запуск

#### Вариант 1: Локальный запуск (рекомендуется для разработки)

1. **Установите зависимости:**
   ```bash
   uv sync
   ```

2. **Настройте конфигурацию:**
   
   Скопируйте примеры конфигурационных файлов:
   ```bash
   cp config.yaml.example config.yaml
   cp agents.yaml.example agents.yaml
   ```
   
   Отредактируйте `config.yaml` и добавьте настройки Confluence:
   ```yaml
   confluence:
     base_url: "https://your-confluence.com"
     username: "your-email@company.com"
     api_token: "your-api-token"
   ```

3. **Запустите агента:**
   ```bash
   uv run python sgr_deep_research
   ```
   
   Агент будет доступен по адресу: `http://localhost:8020`

#### Вариант 2: Запуск через Docker (рекомендуется для продакшена)

1. **Перейдите в директорию сервисов:**
   ```bash
   cd services
   ```

2. **Настройте переменные окружения:**
   
   Создайте файл `.env` или отредактируйте `docker-compose.yml`:
   ```yaml
   environment:
     - CONFLUENCE_BASE_URL=https://your-confluence.com
     - CONFLUENCE_USERNAME=your-email@company.com
     - CONFLUENCE_API_TOKEN=your-api-token
   ```

3. **Запустите контейнер:**
   ```bash
   docker compose up -d
   ```
   
   Агент будет доступен по адресу: `http://localhost:8020`

### Интеграция с Open WebUI

После запуска агента вы можете добавить его в Open WebUI:

1. **Откройте Open WebUI** и перейдите в настройки
2. **Добавьте новое подключение:**
   - **Base URL:** `http://localhost:8020/v1`
   - **API Key:** (оставьте пустым или используйте любое значение)
3. **Выберите модель** `sgr_tool_calling_agent_confluence`
4. **Начните диалог** с агентом!

### Примеры использования

```
Пользователь: Найди документацию по проекту "Альфа"

Агент: 🔍 Ищу документацию о проекте "Альфа" в Confluence...

📄 Проект Альфа: Обзор

На основе анализа документации в Confluence найдена следующая информация:

### 🎯 Основные детали
- **Название**: Проект Альфа
- **Статус**: В разработке
- **Команда**: 12 человек

### 🔗 Источники
- [Проект Альфа - Обзор](https://confluence.company.com/page/123)
- [Техническая документация](https://confluence.company.com/page/456)
```

### Доступные агенты

Проект включает несколько предконфигурированных агентов:

- **`sgr_tool_calling_agent_confluence`** — для работы с Confluence (рекомендуется)
- **`sgr_agent`** — универсальный исследовательский агент с веб-поиском
- **`tool_calling_agent`** — базовый агент с поддержкой инструментов

### Конфигурация

Основные настройки находятся в файлах:

- **`config.yaml`** — конфигурация LLM, Confluence, логирования
- **`agents.yaml`** — определения агентов, инструментов и промптов
- **`logging_config.yaml`** — настройки логирования

📚 **Подробная документация:** [Confluence Agent Guide](docs/CONFLUENCE_AGENT.md)

Также см. общую [документацию проекта](https://github.com/vamplabAI/sgr-deep-research/wiki).

______________________________________________________________________

## Documentation

> **Get started quickly with our documentation:**

- **[Project Wiki](https://github.com/vamplabAI/sgr-deep-research/wiki)** - Complete project documentation
- **[Quick Start Guide](https://github.com/vamplabAI/sgr-deep-research/wiki/SGR-Quick-Start)** - Get up and running in minutes
- **[API Documentation](https://github.com/vamplabAI/sgr-deep-research/wiki/SGR-Description-API)** - REST API reference with examples

______________________________________________________________________

## Benchmarking

![SimpleQA Benchmark Comparison](docs/simpleqa_benchmark_comparison.png)

**Performance Metrics on gpt-4.1-mini:**

- **Accuracy:** 86.08%
- **Correct:** 3,724 answers
- **Incorrect:** 554 answers
- **Not Attempted:** 48 answers

More detailed benchmark results are available [here](benchmark/simpleqa_benchmark_results.md).

______________________________________________________________________

## Open-Source Development Team

*All development is driven by pure enthusiasm and open-source community collaboration. We welcome contributors of all skill levels!*

- **SGR Concept Creator** // [@abdullin](https://t.me/llm_under_hood)
- **Project Coordinator & Vision** // [@VaKovaLskii](https://t.me/neuraldeep)
- **Lead Core Developer** // [@virrius](https://t.me/virrius_tech)
- **API Development** // [Pavel Zloi](https://t.me/evilfreelancer)
- **Hybrid FC research** // [@Shadekss](https://t.me/Shadekss)
- **DevOps & Deployment** // [@mixaill76](https://t.me/mixaill76)

If you have any questions - feel free to join our [community chat](https://t.me/sgragentcore)↗️ or reach out [Valerii Kovalskii](https://www.linkedin.com/in/vakovalskii/)↗️.

## Special Thanks To:

This project is developed by the **neuraldeep** community. It is inspired by the Schema-Guided Reasoning (SGR) work and [SGR Agent Demo](https://abdullin.com/schema-guided-reasoning/demo)↗️ delivered by "LLM Under the Hood" community and AI R&D Hub of [TIMETOACT GROUP Österreich](https://www.timetoact-group.at)↗️

Recent benchmarks and validation experiments were conducted in collaboration with the AI R&D team at red_mad_robot. The lab operates at the intersection of fundamental science and real-world business challenges, running applied experiments and building scalable AI solutions with measurable value.

Learn more about the company: [redmadrobot.ai](https://redmadrobot.ai/) ↗️

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=vamplabAI/sgr-deep-research&type=Date)](https://star-history.com/#vamplabAI/sgr-deep-research&Date)
