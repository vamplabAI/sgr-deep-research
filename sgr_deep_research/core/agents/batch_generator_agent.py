"""Специализированный агент для генерации batch-запросов по теме."""

import logging
from typing import List, Dict, Any
from pydantic import BaseModel, Field

from sgr_deep_research.core.agents.base_agent import BaseAgent
from sgr_deep_research.services.tavily_search import TavilySearchService
from sgr_deep_research.settings import get_config

logger = logging.getLogger(__name__)


class BatchQuery(BaseModel):
    """Модель одного исследовательского запроса."""

    id: int = Field(description="Номер запроса (1-N)")
    query: str = Field(description="Исследовательский запрос на языке темы")
    query_en: str = Field(description="Тот же запрос на английском языке")
    aspect: str = Field(description="Аспект темы (история, экономика, культура, технологии и т.д.)")
    scope: str = Field(description="Масштаб исследования (обзор, детали, сравнение, анализ)")
    suggested_depth: int = Field(description="Рекомендуемый уровень глубины (0-5)", ge=0, le=5)


class BatchPlan(BaseModel):
    """План batch-исследования."""

    topic: str = Field(description="Исходная тема исследования")
    total_queries: int = Field(description="Общее количество запросов")
    languages: List[str] = Field(description="Языки для исследования")
    queries: List[BatchQuery] = Field(description="Список исследовательских запросов")


class BatchGeneratorAgent(BaseAgent):
    """Агент для генерации множественных исследовательских запросов по теме."""

    def __init__(
        self,
        topic: str,
        count: int = 10,
        languages: List[str] = None,
        use_streaming: bool = False,
        with_search: bool = True,
    ):
        """
        Инициализация агента генерации batch-запросов.

        Args:
            topic: Основная тема для исследования
            count: Количество запросов для генерации
            languages: Языки для исследования (по умолчанию: русский, английский)
            use_streaming: Использовать ли потоковый режим
            with_search: Использовать ли поиск для актуализации запросов
        """
        self.topic = topic
        self.count = count
        self.languages = languages or ["ru", "en"]
        self.with_search = with_search
        self._search_service = TavilySearchService() if with_search else None

        # Используем простую задачу для базового класса
        super().__init__(
            task=f"Генерация {count} исследовательских запросов по теме: {topic}",
            toolkit=None,
            max_iterations=1,  # Нужен только один вызов LLM
            use_streaming=use_streaming,
        )

    def _perform_research_search(self) -> str:
        """Выполняет поиск для получения актуальной информации по теме."""
        if not self.with_search or not self._search_service:
            return ""

        try:
            logger.info(f"🔍 Выполняем поиск по теме: {self.topic}")
            # Простой вызов поиска, как в WebSearchTool
            search_results = self._search_service.search(
                query=self.topic,
                max_results=8,
            )

            if not search_results:
                return ""

            # Формируем краткий контекст из результатов поиска
            context = "АКТУАЛЬНАЯ ИНФОРМАЦИЯ ПО ТЕМЕ:\n\n"
            for i, source in enumerate(search_results[:5], 1):  # Топ-5 результатов
                context += f"{i}. **{source.title}**\n"
                # Используем snippet или full_content
                content = source.snippet or source.full_content
                if content:
                    # Берем первые 200 символов для краткости
                    snippet = content[:200] + "..." if len(content) > 200 else content
                    context += f"   {snippet}\n"
                context += f"   Источник: {source.url}\n\n"

            return context

        except Exception as e:
            logger.warning(f"Поиск не удался: {e}")
            return ""

    def _get_system_prompt(self, search_context: str = "") -> str:
        """Создает системный промпт для генерации запросов."""
        base_prompt = f"""Ты - эксперт по планированию исследований. Твоя задача: создать {self.count} простых и конкретных исследовательских запросов по теме "{self.topic}".

{search_context}

ВАЖНО: СОЗДАВАЙ ПРОСТЫЕ И ПРЯМЫЕ ВОПРОСЫ:
1. Каждый запрос должен быть КОРОТКИМ (максимум 1-2 предложения)
2. Используй ПРОСТЫЕ формулировки, избегай сложных академических терминов
3. Каждый запрос должен быть КОНКРЕТНЫМ и ФАКТИЧЕСКИМ
4. НЕ СОЗДАВАЙ вопросы, требующие дополнительных уточнений
5. Предпочитай вопросы "Что", "Когда", "Где", "Как" вместо сложного анализа
6. Уровень глубины: 0-2 (простые и средние вопросы)

ЯЗЫКИ: {', '.join(self.languages)}

НЕ СОЗДАВАЙ сложные академические вопросы с множественными подвопросами или требующие глубокого анализа.

Создай план исследования в формате JSON согласно схеме BatchPlan."""

        return base_prompt

    async def generate_batch_plan(self) -> BatchPlan:
        """Генерирует план batch-исследования."""
        try:
            # Выполняем поиск для получения актуального контекста
            search_context = self._perform_research_search()

            # Получаем клиент OpenAI
            config = get_config()
            from openai import AsyncOpenAI, AsyncAzureOpenAI

            if config.azure and config.azure.api_key:
                # Azure OpenAI configuration
                client = AsyncAzureOpenAI(
                    azure_endpoint=config.azure.base_url,
                    api_key=config.azure.api_key,
                    api_version=config.azure.api_version,
                )
                model = config.azure.deployment_name
            elif config.openai and config.openai.api_key:
                client = AsyncOpenAI(api_key=config.openai.api_key, base_url=config.openai.base_url)
                model = config.openai.model
            else:
                raise ValueError("Не настроены OpenAI или Azure OpenAI API ключи")

            # Создаем запрос с structured output и актуальным контекстом
            completion = await client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt(search_context)},
                    {
                        "role": "user",
                        "content": f"Создай план для {self.count} исследовательских запросов по теме: {self.topic}",
                    },
                ],
                response_format=BatchPlan,
                # Убираем temperature для GPT-5 - поддерживает только default (1)
            )

            batch_plan = completion.choices[0].message.parsed

            logger.info(f"Сгенерирован план из {len(batch_plan.queries)} запросов по теме: {self.topic}")
            return batch_plan

        except Exception as e:
            logger.error(f"Ошибка при генерации batch-плана: {e}")
            # Возвращаем исключение
            raise e

    async def execute(self) -> BatchPlan:
        """Выполняет генерацию batch-плана."""
        return await self.generate_batch_plan()
