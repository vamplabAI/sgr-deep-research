# 🚀 Quick Start: Confluence Agent за 5 минут

Быстрый старт для запуска Confluence Research Agent.

## Шаг 1: Установка (1 минута)

```bash
# Клонируйте репозиторий
git clone https://github.com/vamplabAI/sgr-deep-research.git
cd sgr-deep-research

# Установите зависимости
uv sync
```

## Шаг 2: Конфигурация (2 минуты)

```bash
# Скопируйте примеры конфигов
cp config.yaml.example config.yaml
cp agents.yaml.example agents.yaml
```

Отредактируйте `config.yaml`:

```yaml
llm:
  model: "gpt-4o-mini"
  api_key: "your-openai-key"  # Или через OPENAI_API_KEY

confluence:
  base_url: "https://your-confluence.com"
  username: "your-email@company.com"
  api_token: "your-confluence-token"
```

**Как получить Confluence API Token:**
1. Перейдите в https://id.atlassian.com/manage-profile/security/api-tokens
2. Нажмите "Create API token"
3. Скопируйте токен

## Шаг 3: Запуск (30 секунд)

```bash
uv run python sgr_deep_research
```

Агент запустится на `http://localhost:8020`

## Шаг 4: Тест (30 секунд)

Проверьте работу:

```bash
curl http://localhost:8020/health
```

Или откройте в браузере: http://localhost:8020/docs

## Шаг 5: Использование (1 минута)

### Вариант A: Через Open WebUI

1. Откройте Open WebUI
2. Settings → Connections → Add Connection
3. Base URL: `http://localhost:8020/v1`
4. Выберите модель `sgr_tool_calling_agent_confluence`
5. Начните диалог!

### Вариант B: Через Python

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8020/v1",
    api_key="dummy"
)

response = client.chat.completions.create(
    model="sgr_tool_calling_agent_confluence",
    messages=[
        {"role": "user", "content": "Найди документацию по проекту Alpha"}
    ],
    stream=True
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### Вариант C: Через curl

```bash
curl -X POST http://localhost:8020/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "sgr_tool_calling_agent_confluence",
    "messages": [
      {"role": "user", "content": "Найди проект Alpha"}
    ],
    "stream": true
  }'
```

## 🎉 Готово!

Теперь вы можете:
- Задавать вопросы о документации в Confluence
- Искать проекты, встречи, технические руководства
- Получать структурированные ответы со ссылками на источники

## 📚 Что дальше?

- [Подробная документация](docs/CONFLUENCE_AGENT.md)
- [Примеры использования](examples/confluence_agent_example.py)
- [Настройка агентов](docs/AGENT_CONFIGURATION.md)
- [Community Chat](https://t.me/sgragentcore)

## ⚡ Docker Quick Start

Если предпочитаете Docker:

```bash
cd services
docker compose up -d
```

Агент будет доступен на `http://localhost:8020`

## 🔧 Troubleshooting

**Проблема:** "Connection refused"
```bash
# Проверьте, что агент запущен
ps aux | grep sgr_deep_research

# Проверьте порт
lsof -i :8020
```

**Проблема:** "Confluence authentication failed"
```bash
# Проверьте токен
curl -u your-email@company.com:your-token \
  https://your-confluence.com/rest/api/content
```

**Проблема:** "Model not found"
```bash
# Проверьте доступные модели
curl http://localhost:8020/v1/models
```

## 💡 Полезные команды

```bash
# Просмотр логов
tail -f logs/agent_*.log

# Остановка агента
pkill -f sgr_deep_research

# Обновление зависимостей
uv sync --upgrade

# Запуск тестов
pytest tests/
```

---

**Нужна помощь?** Присоединяйтесь к [Community Chat](https://t.me/sgragentcore)
