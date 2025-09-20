"""Prefect flow for individual research operations."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from prefect import flow, task
from prefect.artifacts import create_markdown_artifact

from sgr_deep_research.core.agents.sgr_tools_agent import SGRToolCallingResearchAgent
from sgr_deep_research.core.models import AgentStatesEnum

import logging

logger = logging.getLogger("prefect")


async def run_research_agent_task(
    query: str,
    deep_level: int = 0,
    result_dir: Optional[str] = None,
    no_clarifications: bool = False,
) -> Dict[str, Any]:
    """Task для выполнения одного исследовательского запроса."""

    logger.info(f"🚀 Запуск агента: {query}")

    base_steps = 5
    base_searches = 3

    # Создаем агента
    agent = SGRToolCallingResearchAgent(
        task=query,
        max_iterations=base_steps * (deep_level * 3 + 1),
        max_searches=base_searches * (deep_level + 1),
        use_streaming=False,
    )

    # Устанавливаем deep_level для использования в параметрах модели
    if deep_level > 0:
        agent._deep_level = deep_level

    # Временно изменяем конфигурацию для result_dir если передан
    original_reports_dir = None
    if result_dir:
        from sgr_deep_research.settings import get_config

        config = get_config()
        original_reports_dir = config.execution.reports_dir
        config.execution.reports_dir = result_dir

        # Запуск агента
        logger.info(f"▶️ Начинаем выполнение агента...")

        # Если no_clarifications=True, принудительно отключаем уточнения
        if no_clarifications:
            # Устанавливаем флаг что уточнения не нужны (пропускаем если поле не существует)
            try:
                agent._context.disable_clarifications = True
                logger.info(f"🚫 Режим без уточнений - агент будет работать с имеющейся информацией")
            except (ValueError, AttributeError):
                logger.info(f"🚫 Режим без уточнений (автоматически - поле disable_clarifications недоступно)")

        await agent.execute()

        # Получение результата - читаем файл отчета если агент его создал
        final_answer = ""
        
        if hasattr(agent._context, 'last_report_path') and agent._context.last_report_path:
            try:
                with open(agent._context.last_report_path, "r", encoding="utf-8") as f:
                    final_answer = f.read()
                logger.info(f"📄 Найден отчет: {Path(agent._context.last_report_path).name}")
            except Exception as e:
                logger.warning(f"Не удалось прочитать отчет: {e}")

        # Получаем источники и статистику
        sources = list(agent._context.sources.values())
        stats = agent.metrics.format_stats()

        # Создаем Prefect artifact с результатом
        try:
            create_markdown_artifact(
                key=f"research-result-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                markdown=final_answer or "Отчет не найден",
                description=f"Исследование: {query[:50]}..."
            )
            logger.info(f"📊 Создан Prefect artifact")
        except Exception as e:
            logger.warning(f"Не удалось создать Prefect artifact: {e}")

        logger.info(f"✅ Агент завершил работу")

        return {
            "status": "COMPLETED",
            "answer": final_answer,
            "sources": [{"number": s.number, "url": s.url, "title": s.title} for s in sources],
            "stats": stats,
            "model": agent.model_name,
            "deep_level": deep_level,
        }


@flow(name="research-flow")
async def research_flow(
    query: str,
    deep_level: int = 0,
    output_file: Optional[str] = None,
    result_dir: Optional[str] = None,
    clarifications: bool = False,
    no_clarifications: bool = False,
) -> Dict[str, Any]:
    """Prefect flow для выполнения одного исследования."""

    logger.info(f"🔄 Запуск research flow для запроса: {query}")

    # Выполняем исследование
    result = await run_research_agent_task(
        query=query,
        deep_level=deep_level,
        result_dir=result_dir,
        no_clarifications=no_clarifications,
    )

    # Сохраняем результат в файл если указан
    if output_file and result.get("status") == "COMPLETED":
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# Результат исследования\n\n")
            f.write(f"**Запрос:** {query}\n\n")
            f.write(f"**Агент:** {result.get('agent_type', 'Unknown')}\n\n")
            f.write(f"**Модель:** {result.get('model', 'Unknown')}\n\n")
            if deep_level > 0:
                f.write(f"**Глубина исследования:** {deep_level}\n\n")
            f.write("## Ответ\n\n")
            f.write(result.get("answer", ""))

            sources = result.get("sources", [])
            if sources:
                f.write("\n\n## Источники\n\n")
                for source in sources:
                    f.write(f"{source['number']}. [{source['title'] or 'Источник'}]({source['url']})\n")

        logger.info(f"💾 Результат сохранен в: {output_path}")

    return result


if __name__ == "__main__":
    import asyncio

    async def main():
        """Simple main function to run research on Bashkir history."""
        query = "История башкир: происхождение, культура, традиции, важные исторические события"

        result = await research_flow(
            query=query,
            deep_level=1,
            output_file="reports/bashkir_history_research.md",
            result_dir="reports",
        )

    # Run the research
    asyncio.run(main())
