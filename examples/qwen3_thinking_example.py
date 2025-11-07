"""Пример использования SGRQwen3ThinkingAgent для работы с thinking моделями qwen3.

Показывает, как использовать агента с моделями qwen3-thinking, которые работают через Function Calling вместо Structured Output.
"""

import asyncio
import logging

import httpx
from openai import AsyncOpenAI

from sgr_deep_research.core.agent_config import GlobalConfig
from sgr_deep_research.core.agents.sgr_qwen3_thinking_agent import SGRQwen3ThinkingAgent
from sgr_deep_research.core.tools import (
    ClarificationTool,
    CreateReportTool,
    FinalAnswerTool,
    WebSearchTool,
)

logging.basicConfig(level=logging.INFO)


async def main():
    """Основной пример использования SGRQwen3ThinkingAgent."""
    
    # 1. Загружаем глобальную конфигурацию из config.yaml
    config = GlobalConfig.from_yaml("config.yaml")
    
    # 2. Создаем AsyncOpenAI клиент
    client_kwargs = {
        "base_url": config.llm.base_url,
        "api_key": config.llm.api_key
    }
    if config.llm.proxy:
        client_kwargs["http_client"] = httpx.AsyncClient(proxy=config.llm.proxy)
    
    openai_client = AsyncOpenAI(**client_kwargs)
    
    # 3. Определяем задачу для агента
    task = (
        "Найди информацию о Schema-Guided Reasoning (SGR) и объясни, "
        "как эта концепция применяется в современных LLM агентах"
    )
    
    # 4. Создаем агента с нужными инструментами
    agent = SGRQwen3ThinkingAgent(
        task=task,
        openai_client=openai_client,
        llm_config=config.llm,
        prompts_config=config.prompts,
        execution_config=config.execution,
        toolkit=[
            WebSearchTool,
            CreateReportTool,
            ClarificationTool,
            FinalAnswerTool,
        ],
    )
    
    # 5. Запускаем выполнение задачи
    print(f"Запуск агента с задачей: {task}\n")
    await agent.execute()
    

async def example_with_clarification():
    """Пример с использованием уточнений."""
    
    config = GlobalConfig.from_yaml("config.yaml")
    
    client_kwargs = {
        "base_url": config.llm.base_url,
        "api_key": config.llm.api_key
    }
    if config.llm.proxy:
        client_kwargs["http_client"] = httpx.AsyncClient(proxy=config.llm.proxy)
    
    openai_client = AsyncOpenAI(**client_kwargs)
    
    task = "Исследуй технологию, о которой я думаю"
    
    agent = SGRQwen3ThinkingAgent(
        task=task,
        openai_client=openai_client,
        llm_config=config.llm,
        prompts_config=config.prompts,
        execution_config=config.execution,
        toolkit=[
            WebSearchTool,
            ClarificationTool,
            FinalAnswerTool,
        ],
    )
    
    # Запускаем агента в отдельной задаче
    agent_task = asyncio.create_task(agent.execute())
    
    # Ждем, пока агент запросит уточнение
    await asyncio.sleep(5)
    
    # Предоставляем уточнение
    if agent._context.state.value == "waiting_for_clarification":
        clarification = "Я думаю о Schema-Guided Reasoning (SGR)"
        await agent.provide_clarification(clarification)
    
    # Ждем завершения выполнения
    await agent_task
    
    print("\nЗадача с уточнением выполнена")


if __name__ == "__main__":
    # Запускаем основной пример
    asyncio.run(main())
    
    # Раскомментируйте для запуска примера с уточнением
    # asyncio.run(example_with_clarification())
