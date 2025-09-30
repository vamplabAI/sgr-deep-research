# SGR Deep Research API - Frontend Documentation

## Обзор

SGR Deep Research API предоставляет OpenAI-совместимый интерфейс для работы с исследовательскими агентами. API поддерживает только потоковый режим (streaming) и предназначен для создания интерактивных приложений исследования.

**Базовый URL:** `http://0.0.0.0:8010`

## Доступные агенты

### 1. SGR Agent (`sgr_agent`)
**Основной агент SGR** - использует структурированное рассуждение для глубокого исследования.

**Характеристики:**
- Стримит JSON reasoning поэтапно
- Всегда запрашивает уточнения для неясных запросов
- Не завершается `[DONE]` - ждет ответа пользователя

### 2. SGR Tool Calling Agent (`sgr_tool_calling_agent`)
**SGR с native function calling** - использует OpenAI tool calling для выбора инструментов.

**Характеристики:**
- Стримит tool_calls arguments по частям
- Завершается `"finish_reason": "tool_calls"`
- Включает usage статистику
- Запрашивает уточнения

### 3. SGR Auto Tool Calling Agent (`sgr_auto_tool_calling_agent`)
**Автоматический режим** - агент сам решает вызывать ли инструменты.

**Характеристики:**
- Стримит tool_calls arguments по частям
- Завершается `"finish_reason": "stop"`
- **Полностью завершается** - не ждет ответа
- Может не выполнять clarification

### 4. SGR SO Tool Calling Agent (`sgr_so_tool_calling_agent`)
**Structured Output версия** - практически идентичен SGR Tool Calling Agent.

**Характеристики:**
- Структура идентична `sgr_tool_calling_agent`
- Стримит tool_calls arguments по частям
- Запрашивает уточнения

### 5. Tool Calling Agent (`tool_calling_agent`)
**Базовый tool calling** - полагается на native function calling LLM.

**Характеристики:**
- **Уникальная структура**: каждый чанк обернут в `"type":"chunk"` + `"snapshot"`
- Использует русский язык в JSON аргументах
- Включает `parsed_arguments` в snapshot

## API Endpoints

### 1. Создание чат-завершения
```http
POST /v1/chat/completions
```

**Тело запроса:**
```json
{
  "model": "sgr_agent",
  "messages": [
    {"role": "user", "content": "Найди цену биткоина"}
  ],
  "stream": true
}
```

**Параметры:**
- `model` - ID агента или существующий agent_id для уточнений
- `messages` - массив сообщений чата
- `stream` - должен быть `true` (единственный поддерживаемый режим)

### 2. Получить доступные модели
```http
GET /v1/models
```

**Ответ:**
```json
{
  "data": [
    {"id": "sgr_agent", "object": "model", "created": 1234567890, "owned_by": "sgr-deep-research"},
    {"id": "sgr_tool_calling_agent", "object": "model", "created": 1234567890, "owned_by": "sgr-deep-research"}
  ],
  "object": "list"
}
```

### 3. Получить состояние агента
```http
GET /agents/{agent_id}/state
```

**Ответ:**
```json
{
  "agent_id": "sgr_agent_47217627-d8e4-4618-8899-bf0c13b0688d",
  "task": "Найди цену биткоина",
  "state": "waiting_for_clarification",
  "iteration": 2,
  "searches_used": 1,
  "clarifications_used": 0,
  "sources_count": 5,
  "current_step_reasoning": {
    "reasoning_steps": ["..."],
    "current_situation": "...",
    "plan_status": "Not started",
    "enough_data": false,
    "remaining_steps": ["..."],
    "task_completed": false,
    "function": {
      "tool_name_discriminator": "websearchtool",
      "query": "текущая цена биткоина"
    }
  }
}
```

### 4. Список активных агентов
```http
GET /agents
```

**Ответ:**
```json
{
  "agents": [
    {
      "agent_id": "sgr_agent_47217627-d8e4-4618-8899-bf0c13b0688d",
      "task": "Найди цену биткоина",
      "state": "completed"
    }
  ],
  "total": 1
}
```

### 5. Предоставить уточнение агенту
```http
POST /agents/{agent_id}/provide_clarification
```

**Тело запроса:**
```json
{
  "messages": [
    {"role": "user", "content": "Текущая цена на бирже Binance"}
  ],
  "stream": true
}
```

### 6. Проверка здоровья
```http
GET /health
```

**Ответ:**
```json
{
  "status": "healthy",
  "service": "SGR Deep Research API"
}
```

## Форматы потокового ответа

### SGR Agent
```
data: {"type":"chunk","chunk":{"choices":[{"delta":{"content":"{\n  \"reasoning_steps\": ["}}]}}

data: {"type":"chunk","chunk":{"choices":[{"delta":{"content":null},"finish_reason":"stop"}]}}

data: {"id": "chatcmpl-...", "choices": [{"delta": {"tool_calls": [{"id": "1-action", "function": {"name": "clarificationtool", "arguments": "{...}"}}]}}]}

data: {"id": "chatcmpl-...", "choices": [{"delta": {"content": "What specific information are you looking for?\n"}}]}
```

### SGR Tool Calling Agent
```
data: {"choices":[{"delta":{"tool_calls":[{"function":{"arguments":"reasoning"}}]}}]}

data: {"choices":[{"delta":{"tool_calls":[{"function":{"arguments":"\":\"The"}}]}}]}

data: {"choices":[{"finish_reason":"tool_calls"}]}

data: {"usage":{"completion_tokens":116,"prompt_tokens":2096,"total_tokens":2212}}

data: {"choices":[{"delta":{"tool_calls":[{"id":"1-action","function":{"name":"clarificationtool","arguments":"{...}"}}]}}]}

data: {"choices":[{"delta":{"content":"What specific information...\n"}}]}
```

### SGR Auto Tool Calling Agent
```
data: {"choices":[{"delta":{"tool_calls":[{"function":{"arguments":"task"}}]}}]}

data: {"choices":[{"delta":{"tool_calls":[{"function":{"arguments":"_completed"}}]}}]}

data: {"choices":[{"finish_reason":"stop"}]}

data: {"usage":{"completion_tokens":121,"prompt_tokens":1820,"total_tokens":1941}}
```

### Tool Calling Agent (уникальная структура)
```
data: {"type":"chunk","chunk":{...},"snapshot":{"id":"...","choices":[{"message":{"tool_calls":[{"function":{"parsed_arguments":{"reasoning":"...","questions":["..."]}}}]}}]},"model":"tool_calling_agent_..."}

data: {"type":"chunk","chunk":{"choices":[{"finish_reason":"tool_calls"}]}}

data: {"choices":[{"delta":{"tool_calls":[{"id":"1-action","function":{"name":"clarificationtool","arguments":"{...}"}}]}}]}

data: {"choices":[{"delta":{"content":"Что именно вы хотите узнать о 'ку'?\n"}}]}
```

## Состояния агентов

- `inited` - агент создан и начал работу
- `reasoning` - агент анализирует задачу
- `searching` - агент выполняет поиск
- `waiting_for_clarification` - агент ждет уточнений от пользователя
- `completed` - задача выполнена
- `error` - произошла ошибка

## Примеры использования

### Базовый запрос
```bash
curl -X POST "http://0.0.0.0:8010/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "sgr_agent",
    "messages": [{"role": "user", "content": "Найди цену биткоина"}],
    "stream": true
  }'
```

### Предоставление уточнения
```bash
# 1. Создать агента и получить agent_id из заголовка X-Agent-ID
curl -X POST "http://0.0.0.0:8010/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "sgr_agent",
    "messages": [{"role": "user", "content": "ку"}],
    "stream": true
  }' \
  -D headers.txt

# 2. Извлечь agent_id из заголовков и предоставить уточнение
AGENT_ID=$(grep "X-Agent-ID" headers.txt | cut -d' ' -f2)
curl -X POST "http://0.0.0.0:8010/agents/$AGENT_ID/provide_clarification" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Найди курс USD к рублю"}],
    "stream": true
  }'
```

### Альтернативный способ с model = agent_id
```bash
# Использовать agent_id как model для уточнения
curl -X POST "http://0.0.0.0:8010/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "sgr_agent_47217627-d8e4-4618-8899-bf0c13b0688d",
    "messages": [{"role": "user", "content": "Найди курс USD к рублю"}],
    "stream": true
  }'
```

## Обработка ошибок

### HTTP статусы
- `200` - Успешный запрос
- `400` - Неверный запрос (неправильная модель, отсутствующие параметры)
- `404` - Агент не найден
- `501` - Не поддерживается (например, stream=false)

### Примеры ошибок
```json
{
  "detail": "Invalid model 'invalid_agent'. Available models: ['sgr_agent', 'sgr_tool_calling_agent', ...]"
}
```

```json
{
  "detail": "Only streaming responses are supported. Set 'stream=true'"
}
```

```json
{
  "detail": "Agent not found"
}
```

## Рекомендации для фронтенда

### 1. Обработка потоков
```javascript
const response = await fetch('/v1/chat/completions', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    model: 'sgr_agent',
    messages: [{role: 'user', content: 'Найди цену биткоина'}],
    stream: true
  })
});

const reader = response.body.getReader();
const agentId = response.headers.get('X-Agent-ID');

while (true) {
  const {done, value} = await reader.read();
  if (done) break;
  
  const chunk = new TextDecoder().decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = line.slice(6);
      if (data === '[DONE]') return;
      
      try {
        const parsed = JSON.parse(data);
        // Обработать чанк
      } catch (e) {
        console.error('Parse error:', e);
      }
    }
  }
}
```

### 2. Определение типа агента
```javascript
function detectAgentType(chunk) {
  if (chunk.type === "chunk" && chunk.snapshot) {
    return 'tool_calling_agent';
  }
  if (chunk.choices?.[0]?.delta?.tool_calls) {
    return 'sgr_tool_calling_family';
  }
  if (chunk.choices?.[0]?.delta?.content?.includes('reasoning_steps')) {
    return 'sgr_agent';
  }
  return 'unknown';
}
```

### 3. Отслеживание завершения
```javascript
function isStreamComplete(chunks, agentType) {
  const lastChunk = chunks[chunks.length - 1];
  
  switch (agentType) {
    case 'sgr_auto_tool_calling_agent':
      return lastChunk.choices?.[0]?.finish_reason === 'stop';
      
    case 'sgr_agent':
    case 'sgr_tool_calling_agent':
    case 'sgr_so_tool_calling_agent':
    case 'tool_calling_agent':
      // Ищем content с вопросами для пользователя
      return chunks.some(chunk => 
        chunk.choices?.[0]?.delta?.content?.includes('?')
      );
      
    default:
      return false;
  }
}
```

### 4. Извлечение вопросов для уточнения
```javascript
function extractQuestions(chunks) {
  for (const chunk of chunks.reverse()) {
    const content = chunk.choices?.[0]?.delta?.content;
    if (content && content.includes('?')) {
      return content.split('\n').filter(line => line.trim());
    }
  }
  return [];
}
```

## Полезные ссылки

### Официальная документация
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference) - базовая структура API
- [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) - спецификация потоковых событий

### Инструменты разработки
- [Postman Collection](https://www.postman.com/) - для тестирования API
- [curl documentation](https://curl.se/docs/manpage.html) - примеры команд
- [jq tutorial](https://stedolan.github.io/jq/tutorial/) - парсинг JSON в командной строке

### React/JavaScript библиотеки
- [fetch-event-source](https://github.com/Azure/fetch-event-source) - обработка SSE в браузере
- [react-markdown](https://github.com/remarkjs/react-markdown) - рендеринг Markdown ответов
- [SWR](https://swr.vercel.app/) - кэширование и управление состоянием

### TypeScript типы
```typescript
interface ChatMessage {
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
}

interface ChatCompletionRequest {
  model: string;
  messages: ChatMessage[];
  stream: boolean;
}

interface AgentState {
  agent_id: string;
  task: string;
  state: 'inited' | 'reasoning' | 'searching' | 'waiting_for_clarification' | 'completed' | 'error';
  iteration: number;
  searches_used: number;
  clarifications_used: number;
  sources_count: number;
  current_step_reasoning?: any;
}
```

### Примеры интеграции
- [OpenAI JavaScript SDK](https://github.com/openai/openai-node) - официальная библиотека
- [Vercel AI SDK](https://sdk.vercel.ai/) - инструменты для AI приложений
- [LangChain.js](https://js.langchain.com/) - фреймворк для LLM приложений

## Changelog

### v1.0.0
- Начальная версия API
- Поддержка 5 типов агентов
- OpenAI-совместимый интерфейс
- Потоковый режим работы
- Система уточнений

