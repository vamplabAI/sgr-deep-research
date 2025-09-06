"""
SGR Step Tracker - отслеживание шагов выполнения агента.
Мониторит состояние агента и предоставляет детальную информацию о процессе.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from core.models import AgentStatesEnum, SourceData
from core.reasoning_schemas import NextStep


class StepStatus(Enum):
    """Статус выполнения шага."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class StepInfo:
    """Информация о шаге выполнения."""
    step_number: int
    tool_name: str
    status: StepStatus
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    reasoning: str = ""
    result: str = ""
    error: Optional[str] = None

    def complete(self, result: str = ""):
        """Завершение шага."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.status = StepStatus.COMPLETED
        self.result = result

    def fail(self, error: str):
        """Ошибка шага."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.status = StepStatus.FAILED
        self.error = error


@dataclass
class AgentMetrics:
    """Метрики агента."""
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    total_duration: float = 0.0
    searches_used: int = 0
    clarifications_used: int = 0
    sources_found: int = 0
    tokens_used: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    def add_step(self, step: StepInfo):
        """Добавление шага."""
        self.total_steps += 1
        if step.status == StepStatus.COMPLETED:
            self.completed_steps += 1
        elif step.status == StepStatus.FAILED:
            self.failed_steps += 1

    def finish(self):
        """Завершение работы агента."""
        self.end_time = time.time()
        self.total_duration = self.end_time - self.start_time


class SGRStepTracker:
    """Трекер шагов выполнения SGR агента."""

    def __init__(self):
        self.steps: List[StepInfo] = []
        self.metrics = AgentMetrics()
        self.current_step: Optional[StepInfo] = None
        self.agent_state = AgentStatesEnum.INITED
        self.sources: List[SourceData] = []
        self.conversation_history: List[Dict[str, Any]] = []

    def start_step(self, step_number: int, tool_name: str, reasoning: str = "") -> StepInfo:
        """Начало нового шага."""
        # Завершаем предыдущий шаг если есть
        if self.current_step and self.current_step.status == StepStatus.IN_PROGRESS:
            self.current_step.complete()

        # Создаем новый шаг
        new_step = StepInfo(
            step_number=step_number,
            tool_name=tool_name,
            status=StepStatus.IN_PROGRESS,
            start_time=time.time(),
            reasoning=reasoning
        )

        self.steps.append(new_step)
        self.current_step = new_step
        self.metrics.add_step(new_step)

        return new_step

    def complete_current_step(self, result: str = ""):
        """Завершение текущего шага."""
        if self.current_step:
            self.current_step.complete(result)
            # Обновляем метрики
            if self.current_step.status.value == "completed":
                self.metrics.completed_steps += 1
            elif self.current_step.status.value == "failed":
                self.metrics.failed_steps += 1
            self.current_step = None

    def fail_current_step(self, error: str):
        """Ошибка текущего шага."""
        if self.current_step:
            self.current_step.fail(error)
            self.current_step = None

    def update_agent_state(self, state: AgentStatesEnum):
        """Обновление состояния агента."""
        self.agent_state = state

    def update_metrics(self, **kwargs):
        """Обновление метрик."""
        for key, value in kwargs.items():
            if hasattr(self.metrics, key):
                setattr(self.metrics, key, value)

    def add_source(self, source: SourceData):
        """Добавление источника."""
        self.sources.append(source)
        self.metrics.sources_found = len(self.sources)

    def add_conversation_message(self, role: str, content: str, tool_calls: Optional[List[Dict]] = None):
        """Добавление сообщения в историю разговора."""
        message = {
            "role":      role,
            "content":   content,
            "timestamp": time.time()
        }
        if tool_calls:
            message["tool_calls"] = tool_calls

        self.conversation_history.append(message)

    def get_current_status(self) -> Dict[str, Any]:
        """Получение текущего статуса."""
        return {
            "agent_state":         self.agent_state.value,
            "current_step":        self.current_step.step_number if self.current_step else None,
            "current_tool":        self.current_step.tool_name if self.current_step else None,
            "total_steps":         self.metrics.total_steps,
            "completed_steps":     self.metrics.completed_steps,
            "failed_steps":        self.metrics.failed_steps,
            "searches_used":       self.metrics.searches_used,
            "clarifications_used": self.metrics.clarifications_used,
            "sources_found":       self.metrics.sources_found,
            "duration":            time.time() - self.metrics.start_time
        }

    def get_step_summary(self) -> List[Dict[str, Any]]:
        """Получение сводки по шагам."""
        summary = []
        for step in self.steps:
            summary.append({
                "step_number":    step.step_number,
                "tool_name":      step.tool_name,
                "status":         step.status.value,
                "duration":       step.duration,
                "reasoning":      step.reasoning,
                "result_preview": step.result[:100] + "..." if len(step.result) > 100 else step.result,
                "error":          step.error
            })
        return summary

    def get_final_report(self) -> Dict[str, Any]:
        """Получение финального отчета."""
        self.metrics.finish()

        return {
            "metrics":             {
                "total_steps":         self.metrics.total_steps,
                "completed_steps":     self.metrics.completed_steps,
                "failed_steps":        self.metrics.failed_steps,
                "success_rate":        (
                                               self.metrics.completed_steps / self.metrics.total_steps * 100) if
                                       self.metrics.total_steps > 0 else 0,
                "total_duration":      self.metrics.total_duration,
                "searches_used":       self.metrics.searches_used,
                "clarifications_used": self.metrics.clarifications_used,
                "sources_found":       self.metrics.sources_found,
                "tokens_used":         self.metrics.tokens_used
            },
            "steps":               self.get_step_summary(),
            "sources":             [{"title": s.title, "url": s.url, "char_count": s.char_count} for s in self.sources],
            "conversation_length": len(self.conversation_history)
        }

    def reset(self):
        """Сброс трекера."""
        self.steps.clear()
        self.metrics = AgentMetrics()
        self.current_step = None
        self.agent_state = AgentStatesEnum.INITED
        self.sources.clear()
        self.conversation_history.clear()
