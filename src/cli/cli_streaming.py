"""
CLI SGR Streaming - потоковый вывод для командной строки.
Интегрирует SGR агента с интерактивным интерфейсом CLI.
"""

import asyncio
import logging
from typing import Dict, Optional, Any, AsyncGenerator
from rich.live import Live
from rich.console import Console

from core.agent import SGRResearchAgent
from core.models import AgentStatesEnum
from .visualizer import SGRVisualizer
from .step_tracker import SGRStepTracker

logger = logging.getLogger(__name__)


class CLISGRStreaming:
    """Потоковый CLI интерфейс для SGR агента."""

    def __init__(self):
        self.console = Console()
        self.visualizer = SGRVisualizer()
        self.tracker = SGRStepTracker()
        self.agent: Optional[SGRResearchAgent] = None
        self.is_running = False

    async def start_research(self, task: str, max_steps: int = 6) -> AsyncGenerator[Dict[str, Any], None]:
        """Запуск исследования с потоковым выводом."""
        try:
            # Создаем агента
            self.agent = SGRResearchAgent(task=task)
            self.tracker.reset()
            self.visualizer.update_agent_state(AgentStatesEnum.INITED)

            # Запускаем исследование
            self.is_running = True
            research_task = asyncio.create_task(self.agent.execute())

            # Мониторим прогресс
            async for update in self._monitor_agent_progress():
                yield update

            # Ждем завершения
            await research_task

            # Финальный статус
            yield {
                "type":         "completion",
                "agent_id":     self.agent.id,
                "final_report": self.tracker.get_final_report()
            }

        except Exception as e:
            logger.error(f"Research error: {e}")
            yield {
                "type":  "error",
                "error": str(e)
            }
        finally:
            self.is_running = False

    async def _monitor_agent_progress(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Мониторинг прогресса агента."""
        step_number = 0

        while self.is_running and self.agent:
            try:
                # Обновляем состояние
                self.tracker.update_agent_state(self.agent.state)
                self.visualizer.update_agent_state(self.agent.state)

                # Обновляем статистику
                self.tracker.update_metrics(
                    searches_used=self.agent._context.searches_used,
                    clarifications_used=self.agent._context.clarifications_used,
                    sources_found=len(self.agent._context.sources)
                )

                self.visualizer.update_stats(
                    searches_used=self.agent._context.searches_used,
                    clarifications_used=self.agent._context.clarifications_used,
                    sources_count=len(self.agent._context.sources)
                )

                # Обновляем источники
                sources = list(self.agent._context.sources.values())
                self.visualizer.update_sources(sources)

                # Проверяем текущее состояние
                if self.agent._context.current_state:
                    current_state = self.agent._context.current_state
                    step_number += 1

                    # Начинаем новый шаг
                    tool_name = getattr(current_state.function, 'tool', 'unknown')
                    reasoning = getattr(current_state.function, 'reasoning', '')

                    step = self.tracker.start_step(step_number, tool_name, reasoning)

                    # Обновляем визуализатор
                    self.visualizer.update_step(
                        step_number,
                        tool_name,
                        current_state.reasoning_steps
                    )

                    yield {
                        "type":        "step_start",
                        "step_number": step_number,
                        "tool_name":   tool_name,
                        "reasoning":   reasoning,
                        "agent_state": self.agent.state.value
                    }

                    # Обрабатываем специальные состояния
                    if self.agent.state == AgentStatesEnum.WAITING_FOR_CLARIFICATION:
                        yield {
                            "type":      "clarification_needed",
                            "questions": getattr(current_state.function, 'questions', []),
                            "agent_id":  self.agent.id
                        }

                    elif self.agent.state == AgentStatesEnum.COMPLETED:
                        # Завершаем шаг
                        self.tracker.complete_current_step("Research completed")
                        yield {
                            "type":         "research_completed",
                            "agent_id":     self.agent.id,
                            "final_report": self.tracker.get_final_report()
                        }
                        break

                # Небольшая задержка для мониторинга
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                self.tracker.fail_current_step(str(e))
                yield {
                    "type":  "error",
                    "error": str(e)
                }
                break

    async def provide_clarification(self, agent_id: str, clarification: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Предоставление уточнения агенту."""
        if not self.agent or self.agent.id != agent_id:
            yield {
                "type":  "error",
                "error": "Agent not found"
            }
            return

        try:
            # Предоставляем уточнение
            await self.agent.provide_clarification(clarification)

            # Обновляем состояние
            self.tracker.update_agent_state(self.agent.state)
            self.visualizer.update_agent_state(self.agent.state)

            yield {
                "type":          "clarification_provided",
                "agent_id":      agent_id,
                "clarification": clarification
            }

            # Продолжаем мониторинг
            async for update in self._monitor_agent_progress():
                yield update

        except Exception as e:
            logger.error(f"Clarification error: {e}")
            yield {
                "type":  "error",
                "error": str(e)
            }

    def get_agent_status(self) -> Dict[str, Any]:
        """Получение статуса агента."""
        if not self.agent:
            return {"error": "No active agent"}

        return {
            "agent_id":       self.agent.id,
            "task":           self.agent.task,
            "state":          self.agent.state.value,
            "tracker_status": self.tracker.get_current_status(),
            "is_running":     self.is_running
        }

    def render_interface(self):
        """Рендеринг интерфейса."""
        return self.visualizer.render()

    def show_completion(self, report_path: Optional[str] = None):
        """Показ сообщения о завершении."""
        self.visualizer.show_completion_message(report_path)

    def show_error(self, error: str):
        """Показ сообщения об ошибке."""
        self.visualizer.show_error_message(error)

    async def run_interactive(self, task: str) -> None:
        """Запуск интерактивного режима."""
        self.console.print(f"[bold blue]Starting SGR Research:[/bold blue] {task}")
        self.console.print()

        try:
            # Запускаем исследование
            with Live(self.render_interface(), refresh_per_second=2, console=self.console) as live:
                async for update in self.start_research(task):
                    await self._process_update(update, live)
                    # Обновляем интерфейс после каждого обновления
                    live.update(self.render_interface())

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Research interrupted by user[/yellow]")
        except Exception as e:
            self.show_error(str(e))

    async def _process_update(self, update: Dict[str, Any], live: Live) -> None:
        """Обработка обновления и обновление интерфейса."""
        update_type = update.get("type")

        if update_type == "step_start":
            # Шаг начался - интерфейс обновится автоматически
            pass

        elif update_type == "clarification_needed":
            # Показываем вопросы для уточнения
            questions = update.get("questions", [])
            self.console.print("\n[bold yellow]Clarification needed:[/bold yellow]")
            for i, question in enumerate(questions, 1):
                self.console.print(f"  {i}. {question}")

            # Получаем ответ пользователя
            try:
                clarification = self.console.input("\n[bold]Your clarification:[/bold] ")
            except UnicodeDecodeError:
                # Fallback для проблем с кодировкой
                self.console.print("[yellow]Warning: Encoding issue detected. Using fallback input.[/yellow]")
                clarification = input("\nYour clarification: ")

            # Предоставляем уточнение
            agent_id = update.get("agent_id")
            if agent_id:
                async for clarification_update in self.provide_clarification(agent_id, clarification):
                    if clarification_update.get("type") == "error":
                        error_msg = clarification_update.get("error", "Unknown error")
                        self.show_error(error_msg)
                        return
                    # Интерфейс обновится автоматически

        elif update_type == "research_completed":
            # Показываем завершение
            final_report = update.get("final_report", {})
            report_path = final_report.get("report_path")
            self.show_completion(report_path)

        elif update_type == "error":
            # Показываем ошибку
            error_msg = update.get("error", "Unknown error")
            self.show_error(error_msg)

    def stop(self):
        """Остановка исследования."""
        self.is_running = False
        if self.agent:
            # Здесь можно добавить логику для корректной остановки агента
            pass
