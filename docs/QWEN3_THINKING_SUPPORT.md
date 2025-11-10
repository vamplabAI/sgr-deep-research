# Поддержка Qwen3-Thinking моделей в SGR Deep Research

## Обзор

Thinking модели семейства Qwen3 не поддерживают напрямую **Structured Output (SO)**, но отлично работают через **Function Calling (FC)**. Эти модели выдают промежуточные рассуждения вместе с результатами вызова инструментов, что требует специальной обработки для извлечения структурированных данных.

Данная реализация добавляет полную поддержку Qwen3-thinking моделей в рамках архитектуры SGR, обеспечивая универсальность работы как с instruct, так и с thinking моделями.

## Ключевые компоненты

### 1. Утилита конвертации Pydantic в Tools (pydantic_convert.py)

Модуль для автоматического преобразования Pydantic-моделей в формат OpenAI Function Calling:

```python
from sgr_deep_research.core.utils.pydantic_convert import pydantic_to_tools

# Конвертация Pydantic-модели в tools формат
tools = pydantic_to_tools(
    model=MyPydanticModel,
    name="my_function",
    description="Описание функции"
)
```

**Возможности:**
- Автоматическое формирование JSON Schema из Pydantic-моделей
- Поддержка вложенных моделей
- Обработка `Literal`, `Optional`, `Union`, `List`, `Dict`
- Поддержка constraints (min/max, length, pattern)

### 2. Адаптер для Qwen3-Thinking (qwen3_thinking_adapter.py)

Извлекает структурированные ответы из "грязного" вывода thinking-моделей с использованием трех стратегий:

1. **tool_calls с JSON в arguments** - чистый JSON или JSON с рассуждениями
2. **content с тегами `<tool_call>...</tool_call>`** - приоритетный формат
3. **content с чистым JSON** - fallback вариант

```python
from sgr_deep_research.core.adapters.qwen3_thinking_adapter import extract_structured_response

# Извлечение структурированного ответа
result = extract_structured_response(
    response_message=api_response.choices[0].message.model_dump(),
    schema_class=MyPydanticModel,
    tool_name="my_function"
)
```

**Особенности:**
- Robustный парсинг с множественными стратегиями
- Поддержка различных форматов вывода thinking-моделей
- Детальная диагностика ошибок валидации

### 3. SGRQwen3ThinkingAgent

Полноценный SGR агент, адаптированный для работы с thinking-моделями:

```python
from sgr_deep_research.core.agents.sgr_qwen3_thinking_agent import SGRQwen3ThinkingAgent

agent = SGRQwen3ThinkingAgent(
    task="Ваша исследовательская задача",
    openai_client=openai_client,
    llm_config=config.llm,
    prompts_config=config.prompts,
    execution_config=config.execution,
    toolkit=[WebSearchTool, CreateReportTool, FinalAnswerTool]
)

await agent.execute()
```

**Отличия от стандартного SGRResearchAgent:**
- Использует Function Calling вместо Structured Output
- Модифицированный системный промпт с инструкциями для thinking-моделей
- Интеграция с адаптером для извлечения структурированных ответов
- Сохранение всей архитектуры SGR (reasoning → action → evaluation)

## Конфигурация

### Базовая конфигурация (config.yaml)

```yaml
llm:
  api_key: "your-api-key"
  base_url: "https://api.your-provider.com/v1"  # vLLM endpoint
  model: "Qwen/Qwen3-14B-thinking"  # или другая thinking модель
  max_tokens: 8000
  temperature: 0.4
  proxy: "socks5://127.0.0.1:1081"  # опционально

search:
  tavily_api_key: "your-tavily-key"
  max_results: 10

execution:
  max_iterations: 10
  max_searches: 4
  max_clarifications: 3
```

### Определение агента (agents.yaml)

```yaml
agents:
  - name: "qwen3_thinking_agent"
    base_class: "SGRQwen3ThinkingAgent"
    
    llm:
      model: "Qwen/Qwen3-14B-thinking"
      temperature: 0.3
      max_tokens: 12000
    
    execution:
      max_iterations: 15
      max_searches: 6
    
    tools:
      - "WebSearchTool"
      - "ExtractPageContentTool"
      - "CreateReportTool"
      - "ClarificationTool"
      - "FinalAnswerTool"
```

## Использование

### Базовый пример

```python
import asyncio
import httpx
from openai import AsyncOpenAI
from sgr_deep_research.core.agent_config import GlobalConfig
from sgr_deep_research.core.agents.sgr_qwen3_thinking_agent import SGRQwen3ThinkingAgent
from sgr_deep_research.core.tools import (
    WebSearchTool,
    CreateReportTool,
    FinalAnswerTool
)

async def main():
    # Загрузка конфигурации
    config = GlobalConfig.from_yaml("config.yaml")
    
    # Создание OpenAI клиента
    client_kwargs = {
        "base_url": config.llm.base_url,
        "api_key": config.llm.api_key
    }
    if config.llm.proxy:
        client_kwargs["http_client"] = httpx.AsyncClient(proxy=config.llm.proxy)
    
    openai_client = AsyncOpenAI(**client_kwargs)
    
    # Создание агента
    agent = SGRQwen3ThinkingAgent(
        task="Найди последние новости о Schema-Guided Reasoning",
        openai_client=openai_client,
        llm_config=config.llm,
        prompts_config=config.prompts,
        execution_config=config.execution,
        toolkit=[WebSearchTool, CreateReportTool, FinalAnswerTool],
    )
    
    # Выполнение
    await agent.execute()

if __name__ == "__main__":
    asyncio.run(main())
```

### Использование через API

```bash
# Запуск API сервера
uv run python sgr_deep_research

# Использование агента
curl -X POST "http://0.0.0.0:8010/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3_thinking_agent",
    "messages": [
      {
        "role": "user",
        "content": "Исследуй концепцию Schema-Guided Reasoning"
      }
    ]
  }'
```

## Технические детали

### Формат ответа thinking-моделей

Thinking модели могут возвращать данные в нескольких форматах:

**Формат 1: tool_calls с чистым JSON**
```json
{
  "tool_calls": [{
    "type": "function",
    "function": {
      "name": "next_step",
      "arguments": "{\"reasoning_steps\": [...], \"function\": {...}}"
    }
  }]
}
```

**Формат 2: content с тегами tool_call**
```
<thinking>
Промежуточные рассуждения модели...
</thinking>

<tool_call>
{"reasoning_steps": ["step 1", "step 2"], "function": {"tool_name_discriminator": "web_search_tool", ...}}
</tool_call>
```

**Формат 3: content с чистым JSON**
```json
{
  "reasoning_steps": ["step 1", "step 2"],
  "current_situation": "...",
  "function": {
    "tool_name_discriminator": "web_search_tool",
    "query": "..."
  }
}
```

### Системный промпт для thinking-моделей

Агент использует специально адаптированный системный промпт:

```
{base_system_prompt}

## Response Schema for Thinking Models:
You must work strictly according to the following Pydantic schema:

```python
{dynamic_schema}
```

## CRITICAL RULES for Thinking Models:
- You may reason and think through the problem first in your internal monologue
- After reasoning, you MUST provide valid JSON matching the schema above
- Wrap your final JSON in <tool_call>...</tool_call> tags for clarity
- All text fields in JSON must be concise and focused
```
