"""SGR агент для qwen3-thinking моделей.

Thinking модели семейства qwen3 не поддерживают Structured Output (SO),
но отлично работают через Function Calling (FC). Этот агент адаптирует
стандартную архитектуру SGR для работы с thinking моделями.
"""

import inspect
from typing import Type

from openai import AsyncOpenAI

from sgr_deep_research.core.adapters.qwen3_thinking_adapter import extract_structured_response
from sgr_deep_research.core.agent_definition import ExecutionConfig, LLMConfig, PromptsConfig
from sgr_deep_research.core.base_agent import BaseAgent
from sgr_deep_research.core.tools import (
    BaseTool,
    ClarificationTool,
    CreateReportTool,
    FinalAnswerTool,
    NextStepToolsBuilder,
    NextStepToolStub,
    ReasoningTool,
    WebSearchTool,
)
from sgr_deep_research.core.utils.pydantic_convert import pydantic_to_tools


def build_system_prompt_with_schema(schema_class, toolkit: list[Type[BaseTool]], base_prompt: str) -> str:
    """Строит системный промпт со схемой для thinking моделей.
    
    Args:
        schema_class: Pydantic-класс схемы NextStepTools
        toolkit: Список доступных инструментов
        base_prompt: Базовый системный промпт из конфигурации
        
    Returns:
        Системный промпт с встроенной схемой
    """
    try:
        schema_code = inspect.getsource(schema_class)
    except (OSError, TypeError):
        # Если не удалось получить исходный код (динамически созданный класс)
        schema_code = f"# Динамически созданная схема на основе {schema_class.__name__}"
    
    tool_descriptions = "\n".join([
        f"- {tool.tool_name}: {tool.description}" 
        for tool in toolkit
    ])
    
    return f"""{base_prompt}

## Available Tools:
{tool_descriptions}

## Response Schema for Thinking Models:
You must work strictly according to the following Pydantic schema:

```python
{schema_code}
```

## CRITICAL RULES for Thinking Models:
- You may reason and think through the problem first in your internal monologue
- After reasoning, you MUST provide valid JSON matching the schema above
- Wrap your final JSON in <tool_call>...</tool_call> tags for clarity
- All text fields in JSON must be concise and focused
- Example format:
<tool_call>
{{"reasoning_steps": ["step 1", "step 2"], "current_situation": "...", "function": {{"tool_name_discriminator": "tool_name", ...}}}}
</tool_call>"""


class SGRQwen3ThinkingAgent(BaseAgent):
    """Agent for deep research tasks using SGR framework with qwen3-thinking models.
    
    Этот агент адаптирует стандартную архитектуру SGR для работы с thinking моделями,
    используя Function Calling вместо Structured Output.
    """

    name: str = "sgr_qwen3_thinking_agent"

    def __init__(
        self,
        task: str,
        openai_client: AsyncOpenAI,
        llm_config: LLMConfig,
        prompts_config: PromptsConfig,
        execution_config: ExecutionConfig,
        toolkit: list[Type[BaseTool]] | None = None,
    ):
        super().__init__(
            task=task,
            openai_client=openai_client,
            llm_config=llm_config,
            prompts_config=prompts_config,
            execution_config=execution_config,
            toolkit=toolkit,
        )
        self.max_searches = execution_config.max_searches
        # Удаляем ReasoningTool, так как используем свою схему рассуждений
        if ReasoningTool in self.toolkit:
            self.toolkit.remove(ReasoningTool)

    async def _prepare_tools(self) -> Type[NextStepToolStub]:
        """Подготовка инструментов с учетом текущих ограничений контекста."""
        tools = set(self.toolkit)
        if self._context.iteration >= self.max_iterations:
            tools = {
                CreateReportTool,
                FinalAnswerTool,
            }
        if self._context.clarifications_used >= self.max_clarifications:
            tools -= {
                ClarificationTool,
            }
        if self._context.searches_used >= self.max_searches:
            tools -= {
                WebSearchTool,
            }
        return NextStepToolsBuilder.build_NextStepTools(list(tools))

    async def _prepare_context(self) -> list[dict]:
        """Подготовка контекста разговора с системным промптом для thinking моделей."""
        from sgr_deep_research.core.services.prompt_loader import PromptLoader
        
        next_step_schema = await self._prepare_tools()
        base_prompt = PromptLoader.get_system_prompt(self.toolkit, self.prompts_config)
        system_prompt = build_system_prompt_with_schema(next_step_schema, self.toolkit, base_prompt)
        
        return [
            {"role": "system", "content": system_prompt},
            *self.conversation,
        ]

    async def _reasoning_phase(self) -> NextStepToolStub:
        """Фаза рассуждения с использованием Function Calling для thinking моделей."""
        next_step_schema = await self._prepare_tools()
        tool_name = "next_step"
        
        # Конвертируем Pydantic схему в OpenAI tools формат
        tools = pydantic_to_tools(
            next_step_schema,
            name=tool_name,
            description="Determine next reasoning step with adaptive planning"
        )
        
        # Вызываем модель с tools параметром
        response = await self.openai_client.chat.completions.create(
            model=self.llm_config.model,
            messages=await self._prepare_context(),
            tools=tools,
            tool_choice={"type": "function", "function": {"name": tool_name}},
            max_tokens=self.llm_config.max_tokens,
            temperature=self.llm_config.temperature,
        )
        
        message = response.choices[0].message
        
        # Извлекаем структурированный ответ с помощью адаптера
        reasoning: NextStepToolStub = extract_structured_response(
            response_message=message.model_dump(),
            schema_class=next_step_schema,
            tool_name=tool_name
        )
        
        self._log_reasoning(reasoning)
        return reasoning

    async def _select_action_phase(self, reasoning: NextStepToolStub) -> BaseTool:
        """Выбор действия на основе результата фазы рассуждения."""
        tool = reasoning.function
        if not isinstance(tool, BaseTool):
            raise ValueError("Selected tool is not a valid BaseTool instance")
        
        self.conversation.append(
            {
                "role": "assistant",
                "content": reasoning.remaining_steps[0] if reasoning.remaining_steps else "Completing",
                "tool_calls": [
                    {
                        "type": "function",
                        "id": f"{self._context.iteration}-action",
                        "function": {
                            "name": tool.tool_name,
                            "arguments": tool.model_dump_json(),
                        },
                    }
                ],
            }
        )
        self.streaming_generator.add_tool_call(
            f"{self._context.iteration}-action", tool.tool_name, tool.model_dump_json()
        )
        return tool

    async def _action_phase(self, tool: BaseTool) -> str:
        """Выполнение выбранного действия."""
        result = await tool(self._context)
        self.conversation.append(
            {"role": "tool", "content": result, "tool_call_id": f"{self._context.iteration}-action"}
        )
        self.streaming_generator.add_chunk_from_str(f"{result}\n")
        self._log_tool_execution(tool, result)
        return result


if __name__ == "__main__":
    import asyncio
    import httpx
    from sgr_deep_research.core.agent_config import GlobalConfig
    
    async def main():
        # Загружаем конфигурацию
        config = GlobalConfig.from_yaml("config.yaml")
        
        # Создаем OpenAI клиент
        client_kwargs = {
            "base_url": config.llm.base_url,
            "api_key": config.llm.api_key
        }
        if config.llm.proxy:
            client_kwargs["http_client"] = httpx.AsyncClient(proxy=config.llm.proxy)
        
        openai_client = AsyncOpenAI(**client_kwargs)
        
        # Создаем агента
        agent = SGRQwen3ThinkingAgent(
            task="найди информацию о репозитории на гитхаб sgr-deep-research и ответь на вопрос, "
            "какая основная концепция этого репозитория?",
            openai_client=openai_client,
            llm_config=config.llm,
            prompts_config=config.prompts,
            execution_config=config.execution,
            toolkit=[WebSearchTool, CreateReportTool, ClarificationTool, FinalAnswerTool],
        )
        await agent.execute()

    asyncio.run(main())
