"""Prefect flow for individual research operations."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from prefect import flow, task

from sgr_deep_research.core.agents.sgr_tools_agent import SGRToolCallingResearchAgent
from sgr_deep_research.core.models import AgentStatesEnum

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


@task(name="run-research-agent")
async def run_research_agent_task(
    query: str,
    deep_level: int = 0,
    result_dir: Optional[str] = None,
    clarifications: bool = False,
) -> Dict[str, Any]:
    """Task для выполнения одного исследовательского запроса."""

    try:
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

        try:
            # Запуск агента
            logger.info(f"▶️ Начинаем выполнение агента...")
            await agent.execute()

            # Обработка состояния агента
            if agent._context.state == AgentStatesEnum.COMPLETED:
                # Получение результата
                final_answer = ""

                # Проверяем отчеты в папке reports
                reports_dir = Path(result_dir or "reports")
                if reports_dir.exists():
                    report_files = list(reports_dir.glob("*.md"))
                    if report_files:
                        latest_report = max(report_files, key=lambda x: x.stat().st_mtime)
                        if (datetime.now().timestamp() - latest_report.stat().st_mtime) < 300:
                            try:
                                with open(latest_report, "r", encoding="utf-8") as f:
                                    final_answer = f.read()
                                logger.info(f"📄 Найден отчет: {latest_report.name}")
                            except Exception as e:
                                logger.warning(f"Не удалось прочитать отчет: {e}")

                # Получаем источники и статистику
                sources = list(agent._context.sources.values())
                stats = agent.metrics.format_stats()

                logger.info(f"✅ Агент успешно завершил работу")

                return {
                    "status": "COMPLETED",
                    "answer": final_answer,
                    "sources": [{"number": s.number, "url": s.url, "title": s.title} for s in sources],
                    "stats": stats,
                    "model": agent.model_name,
                    "deep_level": deep_level,
                }
            else:
                logger.error(f"❌ Агент завершился с состоянием: {agent._context.state}")
                return {
                    "status": "ERROR",
                    "error": f"Agent finished with state: {agent._context.state}",
                    "stats": agent.metrics.format_stats(),
                }

        finally:
            # Восстанавливаем исходную конфигурацию
            if original_reports_dir is not None:
                from sgr_deep_research.settings import get_config

                config = get_config()
                config.execution.reports_dir = original_reports_dir

    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        import traceback

        logger.error(f"📜 Traceback: {traceback.format_exc()}")
        return {
            "status": "ERROR",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


@flow(name="research-flow")
async def research_flow(
    query: str,
    deep_level: int = 0,
    output_file: Optional[str] = None,
    result_dir: Optional[str] = None,
    clarifications: bool = False,
) -> Dict[str, Any]:
    """Prefect flow для выполнения одного исследования."""

    logger.info(f"🔄 Запуск research flow для запроса: {query}")

    # Выполняем исследование
    result = await run_research_agent_task(
        query=query,
        deep_level=deep_level,
        result_dir=result_dir,
        clarifications=clarifications,
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
            output_file="bashkir_history_research.md",
            result_dir="reports",
        )

    # Run the research
    asyncio.run(main())
