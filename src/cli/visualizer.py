"""
SGR Visualizer - визуализация процесса Schema-Guided Reasoning.
Создает интерактивные диаграммы и прогресс-бары для отслеживания работы агента.
"""

import asyncio
import time
from typing import Dict, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.layout import Layout
from rich.align import Align
from rich import box

from core.models import AgentStatesEnum, SourceData
from core.reasoning_schemas import NextStep


class SGRVisualizer:
    """Визуализатор процесса SGR с интерактивным интерфейсом."""
    
    def __init__(self):
        self.console = Console()
        self.layout = Layout()
        self.progress = None
        self.task_progress = None
        self.current_step = 0
        self.total_steps = 6
        self.agent_state = AgentStatesEnum.INITED
        self.sources_count = 0
        self.searches_used = 0
        self.clarifications_used = 0
        self.current_tool = ""
        self.reasoning_steps = []
        self.sources: List[SourceData] = []
        
    def setup_layout(self):
        """Настройка макета интерфейса."""
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="progress", size=6),
            Layout(name="status", size=8),
            Layout(name="sources", size=10),
            Layout(name="footer", size=3)
        )
        
    def create_header(self) -> Panel:
        """Создание заголовка."""
        title = Text("🧠 SGR Deep Research Agent", style="bold blue")
        subtitle = Text("Schema-Guided Reasoning Research System", style="dim")
        
        return Panel(
            Align.center(f"{title}\n{subtitle}"),
            box=box.DOUBLE,
            style="blue"
        )
    
    def create_progress_section(self) -> Panel:
        """Создание секции прогресса."""
        if not self.progress:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]Step {task.completed}/{task.total}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=self.console
            )
            self.task_progress = self.progress.add_task(
                "SGR Research Progress", 
                total=self.total_steps
            )
        
        # Обновляем прогресс
        self.progress.update(self.task_progress, completed=self.current_step)
        
        return Panel(
            self.progress,
            title="[bold]Research Progress",
            border_style="green"
        )
    
    def create_status_section(self) -> Panel:
        """Создание секции статуса."""
        # Создаем таблицу статуса
        status_table = Table(show_header=False, box=box.ROUNDED)
        status_table.add_column("Property", style="cyan", width=20)
        status_table.add_column("Value", style="white")
        
        # Определяем статус агента
        state_emoji = {
            AgentStatesEnum.INITED: "🚀",
            AgentStatesEnum.RESEARCHING: "🔍",
            AgentStatesEnum.WAITING_FOR_CLARIFICATION: "❓",
            AgentStatesEnum.COMPLETED: "✅",
            AgentStatesEnum.ERROR: "❌"
        }
        
        status_table.add_row(
            "Agent State",
            f"{state_emoji.get(self.agent_state, '❓')} {self.agent_state.value.title()}"
        )
        status_table.add_row("Current Tool", f"🔧 {self.current_tool or 'None'}")
        status_table.add_row("Searches Used", f"🔍 {self.searches_used}/4")
        status_table.add_row("Clarifications", f"❓ {self.clarifications_used}/3")
        status_table.add_row("Sources Found", f"📚 {self.sources_count}")
        
        # Добавляем reasoning steps если есть
        if self.reasoning_steps:
            status_table.add_row("", "")
            status_table.add_row("Reasoning Steps", "")
            for i, step in enumerate(self.reasoning_steps[-3:], 1):  # Показываем последние 3
                status_table.add_row(f"  {i}.", step[:60] + "..." if len(step) > 60 else step)
        
        return Panel(
            status_table,
            title="[bold]Agent Status",
            border_style="yellow"
        )
    
    def create_sources_section(self) -> Panel:
        """Создание секции источников."""
        if not self.sources:
            return Panel(
                Text("No sources found yet...", style="dim"),
                title="[bold]Research Sources",
                border_style="blue"
            )
        
        # Создаем таблицу источников
        sources_table = Table(show_header=True, box=box.ROUNDED)
        sources_table.add_column("#", style="cyan", width=3)
        sources_table.add_column("Title", style="white", width=30)
        sources_table.add_column("URL", style="blue", width=40)
        sources_table.add_column("Content", style="dim", width=20)
        
        for source in self.sources[-5:]:  # Показываем последние 5 источников
            title = source.title or "Untitled"
            if len(title) > 25:
                title = title[:25] + "..."
            
            url = source.url
            if len(url) > 35:
                url = url[:35] + "..."
            
            content_info = f"{source.char_count} chars" if source.char_count > 0 else "Snippet only"
            
            sources_table.add_row(
                str(source.number),
                title,
                url,
                content_info
            )
        
        if len(self.sources) > 5:
            sources_table.add_row("...", f"+{len(self.sources) - 5} more", "", "")
        
        return Panel(
            sources_table,
            title=f"[bold]Research Sources ({len(self.sources)})",
            border_style="green"
        )
    
    def create_footer(self) -> Panel:
        """Создание подвала."""
        footer_text = Text("Press Ctrl+C to stop | Use arrow keys to navigate", style="dim")
        return Panel(
            Align.center(footer_text),
            box=box.ROUNDED,
            style="dim"
        )
    
    def update_agent_state(self, state: AgentStatesEnum):
        """Обновление состояния агента."""
        self.agent_state = state
    
    def update_step(self, step: int, tool: str = "", reasoning_steps: Optional[List[str]] = None):
        """Обновление текущего шага."""
        self.current_step = step
        self.current_tool = tool
        if reasoning_steps:
            self.reasoning_steps = reasoning_steps
    
    def update_stats(self, searches_used: Optional[int] = None, clarifications_used: Optional[int] = None, sources_count: Optional[int] = None):
        """Обновление статистики."""
        if searches_used is not None:
            self.searches_used = searches_used
        if clarifications_used is not None:
            self.clarifications_used = clarifications_used
        if sources_count is not None:
            self.sources_count = sources_count
    
    def update_sources(self, sources: List[SourceData]):
        """Обновление списка источников."""
        self.sources = sources
    
    def render(self) -> Layout:
        """Рендеринг полного интерфейса."""
        self.setup_layout()
        
        self.layout["header"].update(self.create_header())
        self.layout["progress"].update(self.create_progress_section())
        self.layout["status"].update(self.create_status_section())
        self.layout["sources"].update(self.create_sources_section())
        self.layout["footer"].update(self.create_footer())
        
        return self.layout
    
    def show_completion_message(self, report_path: Optional[str] = None):
        """Показ сообщения о завершении."""
        completion_panel = Panel(
            Align.center(
                Text("🎉 Research Completed Successfully!", style="bold green") + 
                (f"\n📄 Report saved: {report_path}" if report_path else "")
            ),
            box=box.DOUBLE,
            style="green"
        )
        self.console.print(completion_panel)
    
    def show_error_message(self, error: str):
        """Показ сообщения об ошибке."""
        error_panel = Panel(
            Align.center(Text(f"❌ Error: {error}", style="bold red")),
            box=box.DOUBLE,
            style="red"
        )
        self.console.print(error_panel)
