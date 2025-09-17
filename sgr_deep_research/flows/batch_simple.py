"""Упрощенный Prefect flow для batch исследований."""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List

from prefect import flow, task

from sgr_deep_research.core.agents.batch_generator_agent import BatchGeneratorAgent
from sgr_deep_research.core.agents import DEFAULT_AGENT
from .research_flow import research_flow

logger = logging.getLogger("prefect")


@task(name="generate-batch-queries")
async def generate_batch_queries_task(
    topic: str,
    count: int,
) -> List[Dict[str, Any]]:
    """Task для генерации списка запросов для batch исследования."""

    logger.info(f"🎯 Генерация {count} запросов по теме: {topic}")

    # Создаем batch generator агента
    generator = BatchGeneratorAgent(topic)
    generator.count = count  # Устанавливаем количество

    # Генерируем план
    batch_plan = await generator.generate_batch_plan()

    # Извлекаем только queries из плана
    queries = []
    for line in batch_plan.queries:
        queries.append({
            "query": line.query, 
            "suggested_depth": line.suggested_depth, 
            "aspect": getattr(line, 'aspect', ''),
            "scope": getattr(line, 'scope', '')
        })

    logger.info(f"✅ Сгенерировано {len(queries)} запросов")
    return queries


@flow(name="batch-simple-flow")
async def batch_simple_flow(
    topic: str,
    count: int = 5,
    agent_type: str = DEFAULT_AGENT,
    max_concurrent: int = 3,
    result_dir: str = "batch_results",
    deep_level: int = 0,
) -> Dict[str, Any]:
    """
    Упрощенный batch flow:
    1. Генерирует список запросов в task
    2. Запускает research subflows параллельно без clarifications
    3. Сохраняет только markdown отчеты
    """

    logger.info(f"🚀 Запуск упрощенного batch исследования: {topic}")
    deep_info = f", deep level {deep_level}" if deep_level > 0 else ""
    logger.info(f"📊 Параметры: {count} запросов, {max_concurrent} параллельно{deep_info}")

    # Генерируем запросы
    queries = await generate_batch_queries_task(topic, count)

    # Создаем директорию для результатов
    result_path = Path(result_dir)
    result_path.mkdir(parents=True, exist_ok=True)

    # Функция для выполнения одного исследования
    async def run_single_research(query_data: Dict[str, Any], index: int):
        query = query_data["query"]
        # Используем общий deep_level для всех запросов в batch
        actual_depth = deep_level if deep_level > 0 else query_data.get("suggested_depth", 0)

        # Создаем безопасное имя файла из запроса
        safe_filename = "".join(c for c in query[:50] if c.isalnum() or c in (" ", "-", "_")).rstrip()
        safe_filename = safe_filename.replace(" ", "_")
        output_file = result_path / f"{index:02d}_{safe_filename}.md"

        logger.info(f"🔍 Запуск исследования {index}: {query}")

        try:
            # Вызываем research flow как subflow БЕЗ clarifications
            result = await research_flow(
                query=query,
                deep_level=actual_depth,
                output_file=str(output_file),
                result_dir=str(result_path),
                no_clarifications=True,  # Ключевой параметр!
            )

            logger.info(f"✅ Завершено исследование {index}: {query[:30]}...")
            return {
                "index": index,
                "query": query,
                "status": result.get("status", "UNKNOWN"),
                "output_file": str(output_file),
                "result": result,
            }

        except Exception as e:
            logger.error(f"❌ Ошибка в исследовании {index}: {e}")
            return {"index": index, "query": query, "status": "ERROR", "error": str(e), "output_file": str(output_file)}

    # Запускаем исследования параллельно с ограничением
    semaphore = asyncio.Semaphore(max_concurrent)

    async def run_with_semaphore(query_data: Dict[str, Any], index: int):
        async with semaphore:
            return await run_single_research(query_data, index)

    # Создаем корутины для всех исследований
    coroutines = [run_with_semaphore(query_data, i + 1) for i, query_data in enumerate(queries)]

    # Выполняем все исследования параллельно
    logger.info(f"🔄 Запуск {len(coroutines)} исследований с ограничением {max_concurrent}")
    results = await asyncio.gather(*coroutines, return_exceptions=True)

    # Подсчитываем статистику
    completed = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "COMPLETED")
    failed = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "ERROR")
    exceptions = sum(1 for r in results if isinstance(r, Exception))

    logger.info(f"📊 Batch завершен: {completed} успешно, {failed} ошибок, {exceptions} исключений")

    return {
        "status": "COMPLETED",
        "topic": topic,
        "total_queries": len(queries),
        "completed": completed,
        "failed": failed,
        "exceptions": exceptions,
        "result_dir": str(result_path),
        "results": [r for r in results if isinstance(r, dict)],
        "queries": queries,
    }
