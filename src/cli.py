"""
SGR Deep Research CLI - интерактивная командная строка.
Запуск: python cli.py "Your research question"
"""

import sys
import asyncio
import argparse
import sys
import os
from pathlib import Path

# Добавляем src в путь для импорта модулей
sys.path.insert(0, str(Path(__file__).parent))

from cli.cli_streaming import CLISGRStreaming
from cli.visualizer import SGRVisualizer
from cli.step_tracker import SGRStepTracker
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()


def print_banner():
    """Печать баннера приложения."""
    banner = """
🧠 SGR Deep Research CLI
Schema-Guided Reasoning Research System
=====================================
    """
    console.print(Panel(
        Text(banner.strip(), style="bold blue"),
        box=box.DOUBLE,
        style="blue"
    ))


def print_help():
    """Печать справки."""
    help_text = """
[bold]Usage:[/bold]
  python cli.py "Your research question"
  python cli.py --interactive
  python cli.py --help

[bold]Examples:[/bold]
  python cli.py "Research BMW X6 2025 prices in Russia"
  python cli.py "Analyze current AI trends in 2024"
  python cli.py "Compare top 5 CRM systems"

[bold]Options:[/bold]
  --interactive, -i    Interactive mode with step-by-step guidance
  --max-steps N        Maximum number of research steps (default: 6)
  --config PATH        Path to configuration file
  --help, -h           Show this help message
    """
    console.print(Panel(
        Text(help_text.strip(), style="white"),
        title="[bold]Help[/bold]",
        border_style="green"
    ))


async def run_research(task: str, max_steps: int = 6, interactive: bool = False):
    """Запуск исследования."""
    try:
        # Создаем CLI streaming
        cli_streaming = CLISGRStreaming()
        
        if interactive:
            # Интерактивный режим
            await cli_streaming.run_interactive(task)
        else:
            # Автоматический режим
            console.print(f"[bold green]Starting research:[/bold green] {task}")
            console.print()
            
            async for update in cli_streaming.start_research(task, max_steps):
                update_type = update.get("type")
                
                if update_type == "step_start":
                    step_num = update.get("step_number")
                    tool_name = update.get("tool_name")
                    console.print(f"[cyan]Step {step_num}:[/cyan] {tool_name}")
                
                elif update_type == "clarification_needed":
                    questions = update.get("questions", [])
                    console.print("\n[yellow]Clarification needed:[/yellow]")
                    for i, question in enumerate(questions, 1):
                        console.print(f"  {i}. {question}")
                    
                    clarification = console.input("\n[bold]Your clarification:[/bold] ")
                    agent_id = update.get("agent_id")
                    
                    async for clarification_update in cli_streaming.provide_clarification(agent_id, clarification):
                        if clarification_update.get("type") == "error":
                            console.print(f"[red]Error:[/red] {clarification_update.get('error')}")
                            return
                
                elif update_type == "research_completed":
                    console.print("\n[bold green]Research completed successfully![/bold green]")
                    final_report = update.get("final_report", {})
                    metrics = final_report.get("metrics", {})
                    console.print(f"Steps completed: {metrics.get('completed_steps', 0)}/{metrics.get('total_steps', 0)}")
                    console.print(f"Sources found: {metrics.get('sources_found', 0)}")
                    console.print(f"Duration: {metrics.get('total_duration', 0):.2f}s")
                
                elif update_type == "error":
                    console.print(f"[red]Error:[/red] {update.get('error')}")
                    return
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Research interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


def main():
    """Главная функция CLI."""

    # Пытаемся установить UTF-8 кодировку
    try:
        if sys.platform.startswith('win'):
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
            sys.stdin = codecs.getreader('utf-8')(sys.stdin.detach())
        else:
            # Для Linux/Mac
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
            sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    except Exception:
        # Если не удалось установить кодировку, продолжаем
        pass
    
    parser = argparse.ArgumentParser(
        description="SGR Deep Research CLI - Interactive Research Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "task",
        nargs="?",
        help="Research question or task"
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode with visual interface"
    )
    
    parser.add_argument(
        "--max-steps",
        type=int,
        default=6,
        help="Maximum number of research steps (default: 6)"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="SGR Deep Research CLI v1.0.0"
    )
    
    args = parser.parse_args()
    
    # Показываем баннер
    print_banner()
    
    # Проверяем аргументы
    if not args.task and not args.interactive:
        print_help()
        return
    
    # Устанавливаем конфигурацию если указана
    if args.config:
        os.environ["APP_CONFIG"] = args.config
    
    # Запускаем исследование
    if args.interactive and not args.task:
        # Интерактивный режим без задачи - запрашиваем у пользователя
        try:
            task = console.input("[bold]Enter your research question:[/bold] ")
        except UnicodeDecodeError:
            # Fallback для проблем с кодировкой
            console.print("[yellow]Warning: Encoding issue detected. Using fallback input.[/yellow]")
            task = input("Enter your research question: ")
        
        if not task.strip():
            console.print("[red]No task provided. Exiting.[/red]")
            return
    else:
        task = args.task
    
    # Запускаем асинхронную функцию
    asyncio.run(run_research(task, args.max_steps, args.interactive))


if __name__ == "__main__":
    main()
