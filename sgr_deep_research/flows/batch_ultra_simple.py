"""Ультра-упрощенные Prefect flows для batch research операций."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from prefect import flow, task
from prefect.futures import wait

from sgr_deep_research.core.agents.batch_generator_agent import BatchGeneratorAgent
from sgr_deep_research.core.agents import DEFAULT_AGENT
from .research_flow import research_flow

logger = logging.getLogger(__name__)


@task(name="generate-batch-plan")
async def generate_batch_plan_task(
    topic: str,
    count: int,
    languages: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Task для генерации плана batch-исследования."""
    
    try:
        logger.info(f"🎯 Генерация плана для {count} запросов по теме: {topic}")
        
        generator = BatchGeneratorAgent(
            topic=topic,
            count=count,
            languages=languages or ["ru", "en"],
        )
        
        batch_plan = await generator.execute()
        
        return {
            "status": "SUCCESS",
            "topic": batch_plan.topic,
            "total_queries": batch_plan.total_queries,
            "languages": batch_plan.languages,
            "queries": [
                {
                    "id": query.id,
                    "query": query.query,
                    "query_en": query.query_en,
                    "aspect": query.aspect,
                    "scope": query.scope,
                    "suggested_depth": query.suggested_depth,
                }
                for query in batch_plan.queries
            ],
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации плана: {e}")
        return {
            "status": "ERROR",
            "error": str(e),
        }


@task(name="save-batch-plan")
def save_batch_plan_task(
    batch_plan: Dict[str, Any],
    batch_name: str,
) -> Path:
    """Task для сохранения плана batch-исследования."""
    
    # Добавляем timestamp для уникальности
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_batch_name = f"{batch_name}_{timestamp}"
    
    # Создаем папку для batch
    batch_dir = Path("batches") / full_batch_name
    batch_dir.mkdir(parents=True, exist_ok=True)
    
    # Создаем простой план - одна строка = один запрос
    plan_file = batch_dir / "plan.txt"
    with open(plan_file, "w", encoding="utf-8") as f:
        f.write(f"# Batch: {full_batch_name}\n")
        f.write(f"# Topic: {batch_plan['topic']}\n")
        f.write(f"# Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Total queries: {batch_plan['total_queries']}\n\n")
        
        for query in batch_plan["queries"]:
            f.write(f"{query['query']}\n")
    
    # Создаем метаданные в JSON
    meta_file = batch_dir / "metadata.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        meta = {
            "batch_name": full_batch_name,
            "original_name": batch_name,
            "topic": batch_plan["topic"],
            "created": datetime.now().isoformat(),
            "total_queries": batch_plan["total_queries"],
            "languages": batch_plan["languages"],
            "queries_meta": [
                {
                    "line": i + 1,
                    "query": query["query"],
                    "query_en": query["query_en"],
                    "aspect": query["aspect"],
                    "scope": query["scope"],
                    "suggested_depth": query["suggested_depth"],
                }
                for i, query in enumerate(batch_plan["queries"])
            ],
        }
        json.dump(meta, f, ensure_ascii=False, indent=2)
    
    logger.info(f"📁 План сохранен в: {batch_dir}")
    return batch_dir


@flow(name="batch-create-flow")
async def batch_create_flow(
    topic: str,
    batch_name: str,
    count: int,
    languages: Optional[List[str]] = None,
) -> Path:
    """Ультра-упрощенный Prefect flow для создания плана batch-исследования."""
    
    logger.info(f"🎯 Создание batch плана '{batch_name}' для темы: {topic}")
    
    # Генерируем план
    batch_plan = await generate_batch_plan_task(
        topic=topic,
        count=count,
        languages=languages,
    )
    
    if batch_plan.get("status") != "SUCCESS":
        raise RuntimeError(f"Ошибка генерации плана: {batch_plan.get('error')}")
    
    # Сохраняем план
    batch_dir = save_batch_plan_task(
        batch_plan=batch_plan,
        batch_name=batch_name,
    )
    
    logger.info(f"✅ Batch план создан: {batch_dir}")
    return batch_dir


@task(name="save-research-result")  
def save_research_result_task(
    line_num: int,
    query: str,
    agent_type: str,
    suggested_depth: int,
    batch_dir: Path,
    result: Dict[str, Any],
) -> bool:
    """Task для сохранения результата исследования."""
    
    try:
        result_dir = batch_dir / f"{line_num:02d}_result"
        result_dir.mkdir(exist_ok=True)
        
        # Сохраняем отчет
        output_file = result_dir / "report.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"# Результат исследования\n\n")
            f.write(f"**Запрос:** {query}\n\n")
            f.write(f"**Агент:** {agent_type}\n\n")
            f.write(f"**Глубина:** {suggested_depth}\n\n")
            f.write("## Ответ\n\n")
            f.write(result.get("answer", "Исследование завершено."))
            
            sources = result.get("sources", [])
            if sources:
                f.write("\n\n## Источники\n\n")
                for source in sources:
                    f.write(f"{source['number']}. [{source['title'] or 'Источник'}]({source['url']})\n")
        
        # Сохраняем метаданные выполнения
        meta_file = result_dir / "execution.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({
                "line_number": line_num,
                "query": query,
                "agent_type": agent_type,
                "suggested_depth": suggested_depth,
                "completed_at": datetime.now().isoformat(),
                "status": "COMPLETED" if result.get("status") == "COMPLETED" else "ERROR",
                "output_file": str(output_file),
                "stats": result.get("stats", {}),
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Результат {line_num} сохранен")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения результата {line_num}: {e}")
        return False


@flow(name="batch-run-flow")
async def batch_run_flow(
    batch_name: str,
    agent_type: str = DEFAULT_AGENT,
    force_restart: bool = False,
    max_concurrent: int = 5,
) -> Dict[str, Any]:
    """
    Ультра-упрощенный Prefect flow для выполнения batch-исследования.
    
    Использует flow.submit() для запуска research subflows параллельно!
    """
    
    logger.info(f"🚀 Запуск batch исследования '{batch_name}'")
    
    # Загружаем план
    batch_dir = Path("batches") / batch_name
    if not batch_dir.exists():
        raise FileNotFoundError(f"Batch '{batch_name}' не найден в: {batch_dir}")
    
    plan_file = batch_dir / "plan.txt"
    meta_file = batch_dir / "metadata.json"
    
    if not plan_file.exists():
        raise FileNotFoundError(f"Файл плана не найден: {plan_file}")
    
    # Загружаем запросы из плана
    queries = []
    with open(plan_file, "r", encoding="utf-8") as f:
        actual_line_num = 0
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line and not line.startswith("#"):
                actual_line_num += 1
                queries.append((actual_line_num, line))
    
    # Загружаем метаданные для глубины
    queries_meta = {}
    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
                for qmeta in meta.get("queries_meta", []):
                    queries_meta[qmeta["line"]] = qmeta
        except Exception as e:
            logger.warning(f"⚠️ Не удалось загрузить метаданные: {e}")
    
    if not queries:
        raise ValueError("Не найдены запросы для выполнения")
    
    # Проверяем что уже выполнено (если не force_restart)
    queries_to_run = queries
    if not force_restart:
        completed_queries = set()
        for line_num, _ in queries:
            result_dir = batch_dir / f"{line_num:02d}_result"
            exec_file = result_dir / "execution.json"
            if exec_file.exists():
                try:
                    with open(exec_file, "r", encoding="utf-8") as f:
                        exec_data = json.load(f)
                        if exec_data.get("status") == "COMPLETED":
                            completed_queries.add(line_num)
                except:
                    pass
        
        queries_to_run = [(ln, q) for ln, q in queries if ln not in completed_queries]
        
        if completed_queries:
            logger.info(f"🔄 Пропускаем {len(completed_queries)} уже выполненных запросов")
    
    if not queries_to_run:
        logger.info("✅ Все запросы уже выполнены!")
        return {
            "status": "COMPLETED",
            "total_queries": len(queries),
            "executed_queries": 0,
            "skipped_queries": len(queries),
        }
    
    logger.info(f"📋 К выполнению: {len(queries_to_run)} из {len(queries)} запросов")
    logger.info(f"🤖 Агент: {agent_type}")
    logger.info(f"⚡ Максимум параллельных subflows: {max_concurrent}")
    
    # 🚀 ПРОСТОЕ РЕШЕНИЕ - используем asyncio.gather для параллельных subflows!
    logger.info("⚡ Запускаем research subflows через asyncio.gather...")
    
    import asyncio
    
    async def run_single_research_subflow(line_num: int, query: str, suggested_depth: int):
        """Запускает один research subflow."""
        logger.info(f"🔄 Запуск research subflow {line_num}: {query[:50]}...")
        
        # Создаем папку для результата
        result_dir = batch_dir / f"{line_num:02d}_result"
        result_dir.mkdir(exist_ok=True)
        
        try:
            # ⚡ ЗАПУСКАЕМ RESEARCH КАК SUBFLOW - ПРОСТО ВЫЗЫВАЕМ!
            result = await research_flow(
                agent_type=agent_type,
                query=query,
                deep_level=suggested_depth,
                output_file=str(result_dir / "report.md"),
                result_dir=str(result_dir),
            )
            
            logger.info(f"✅ Research subflow {line_num} завершен")
            return line_num, query, suggested_depth, result
            
        except Exception as e:
            logger.error(f"❌ Ошибка в research subflow {line_num}: {e}")
            return line_num, query, suggested_depth, {"status": "ERROR", "error": str(e)}
    
    # Создаем корутины для всех запросов  
    coroutines = []
    for line_num, query in queries_to_run:
        # Получаем suggested_depth из метаданных
        suggested_depth = queries_meta.get(line_num, {}).get("suggested_depth", 0)
        coro = run_single_research_subflow(line_num, query, suggested_depth)
        coroutines.append(coro)
    
    # Ограничиваем параллельность семафором
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def run_with_semaphore(coro):
        async with semaphore:
            return await coro
    
    # Выполняем все subflows параллельно с ограничением
    logger.info(f"⏳ Выполняем {len(coroutines)} research subflows с ограничением {max_concurrent}...")
    subflow_results = await asyncio.gather(*[run_with_semaphore(coro) for coro in coroutines])
    
    logger.info(f"✅ Завершено {len(subflow_results)} research subflows")
    
    # Сохраняем результаты
    save_tasks = []
    successful_count = 0
    
    for line_num, query, suggested_depth, result in subflow_results:
        try:
            if result.get("status") == "COMPLETED":
                successful_count += 1
            
            # Запускаем task для сохранения результата
            save_task = save_research_result_task.submit(
                line_num=line_num,
                query=query,
                agent_type=agent_type,
                suggested_depth=suggested_depth,
                batch_dir=batch_dir,
                result=result,
            )
            save_tasks.append(save_task)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки результата subflow {line_num}: {e}")
    
    # Ждем завершения сохранения всех результатов
    if save_tasks:
        wait(save_tasks)
        logger.info(f"💾 Сохранено {len(save_tasks)} результатов")
    
    logger.info(f"🎉 Batch '{batch_name}' завершен!")
    logger.info(f"✅ Успешно: {successful_count}/{len(queries_to_run)}")
    logger.info(f"📁 Результаты в: {batch_dir}")
    
    return {
        "status": "COMPLETED",
        "batch_name": batch_name,
        "total_queries": len(queries),
        "executed_queries": len(queries_to_run),
        "successful_queries": successful_count,
        "failed_queries": len(queries_to_run) - successful_count,
        "skipped_queries": len(queries) - len(queries_to_run),
        "batch_dir": str(batch_dir),
    }