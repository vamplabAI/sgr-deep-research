"""CLI интерфейс для SGR Deep Research агентов."""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Type

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.spinner import Spinner
from rich.text import Text

from sgr_deep_research.core.agents import (
    BaseAgent,
    SGRAutoToolCallingResearchAgent,
    SGRResearchAgent,
    SGRSOToolCallingResearchAgent,
    SGRToolCallingResearchAgent,
    ToolCallingResearchAgent,
)
from sgr_deep_research.settings import get_config

console = Console()

# Доступные агенты
AGENTS: Dict[str, Type[BaseAgent]] = {
    "sgr": SGRResearchAgent,
    "sgr-tools": SGRToolCallingResearchAgent,
    "sgr-auto-tools": SGRAutoToolCallingResearchAgent,
    "sgr-so-tools": SGRSOToolCallingResearchAgent,
    "tools": ToolCallingResearchAgent,
}


def setup_logging(debug: bool = False):
    """Настройка логирования."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )


def display_agents():
    """Показать доступных агентов."""
    console.print("\n[bold cyan]Доступные агенты:[/bold cyan]")
    for key, agent_class in AGENTS.items():
        doc = agent_class.__doc__ or "Нет описания"
        console.print(f"  [green]{key:15}[/green] - {doc.strip().split('.')[0]}")
    console.print()


async def run_agent(agent_type: str, query: str, output_file: str = None):
    """Запустить агента с заданным запросом."""
    if agent_type not in AGENTS:
        console.print(f"[red]Ошибка:[/red] Неизвестный тип агента '{agent_type}'")
        display_agents()
        return

    agent_class = AGENTS[agent_type]
    
    try:
        console.print(f"\n[bold cyan]Инициализация агента:[/bold cyan] {agent_class.__name__}")
        agent = agent_class(query)
        
        console.print(f"[bold cyan]Запрос:[/bold cyan] {query}")
        console.print(f"[bold cyan]Модель:[/bold cyan] {agent.model_name}")
        console.print()
        
        # Запуск агента с прогресс-индикатором
        with Live(Spinner("dots", text="Обработка запроса..."), console=console, refresh_per_second=10):
            await agent.execute()
        
        # Ожидание завершения агента
        from sgr_deep_research.core.models import AgentStatesEnum
        while agent._context.state not in AgentStatesEnum.FINISH_STATES.value:
            await asyncio.sleep(0.1)
        
        # Получение результата из контекста агента
        if agent._context.state == AgentStatesEnum.COMPLETED:
            # Попытка найти сгенерированный отчет
            final_answer = ""
            
            # Проверим последние отчеты в папке reports
            reports_dir = Path("reports")
            if reports_dir.exists():
                # Найти самый новый отчет
                report_files = list(reports_dir.glob("*.md"))
                if report_files:
                    latest_report = max(report_files, key=lambda x: x.stat().st_mtime)
                    # Проверить, что отчет создан недавно (в течение последних 5 минут)
                    if (datetime.now().timestamp() - latest_report.stat().st_mtime) < 300:
                        try:
                            with open(latest_report, 'r', encoding='utf-8') as f:
                                final_answer = f.read()
                            console.print(f"[dim]Найден отчет: {latest_report.name}[/dim]")
                        except Exception as e:
                            console.print(f"[yellow]Не удалось прочитать отчет: {e}[/yellow]")
            
            # Если отчет не найден, попробуем получить из других источников
            if not final_answer:
                if hasattr(agent.streaming_generator, '_buffer'):
                    final_answer = agent.streaming_generator._buffer
                elif hasattr(agent, '_final_answer'):
                    final_answer = agent._final_answer
                elif agent._context.searches:
                    final_answer = agent._context.searches[-1].answer or "Исследование завершено."
                else:
                    final_answer = "Исследование завершено, но результат не найден."
            
            # Отображение результата
            console.print("\n" + "="*80 + "\n")
            console.print(Panel(
                Markdown(final_answer),
                title="[bold green]Результат исследования[/bold green]",
                border_style="green"
            ))
            
            # Отображение источников
            sources = list(agent._context.sources.values())
            if sources:
                console.print(f"\n[bold cyan]Источники ({len(sources)}):[/bold cyan]")
                for source in sources:
                    console.print(f"  {source.number}. [link]{source.url}[/link]")
                    if source.title:
                        console.print(f"     {source.title}")
            
            # Сохранение в файл
            if output_file:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(f"# Результат исследования\n\n")
                    f.write(f"**Запрос:** {query}\n\n")
                    f.write(f"**Агент:** {agent_class.__name__}\n\n")
                    f.write(f"**Модель:** {agent.model_name}\n\n")
                    f.write("## Ответ\n\n")
                    f.write(final_answer)
                    
                    if sources:
                        f.write("\n\n## Источники\n\n")
                        for source in sources:
                            f.write(f"{source.number}. [{source.title or 'Источник'}]({source.url})\n")
                
                console.print(f"\n[green]Результат сохранен в:[/green] {output_path}")
            
            return {"answer": final_answer, "sources": sources}
        else:
            console.print(f"[red]Агент завершился с ошибкой. Состояние:[/red] {agent._context.state}")
            return None
        
    except Exception as e:
        console.print(f"\n[red]Ошибка при выполнении:[/red] {e}")
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            import traceback
            console.print(f"[red]Traceback:[/red]\n{traceback.format_exc()}")
        return None


async def interactive_mode():
    """Интерактивный режим работы."""
    console.print("[bold cyan]🔍 SGR Deep Research - Интерактивный режим[/bold cyan]")
    console.print("Введите 'help' для справки, 'quit' для выхода\n")
    
    current_agent = "sgr-tools"  # По умолчанию
    
    while True:
        try:
            command = Prompt.ask(f"[{current_agent}]", default="").strip()
            
            if not command or command.lower() in ["quit", "exit", "q"]:
                console.print("[yellow]До свидания![/yellow]")
                break
            
            if command.lower() == "help":
                console.print("\n[bold cyan]Команды:[/bold cyan]")
                console.print("  help              - Показать эту справку")
                console.print("  agents            - Показать доступных агентов")
                console.print("  agent <type>      - Переключиться на агента")
                console.print("  quit/exit/q       - Выход")
                console.print("  <запрос>          - Выполнить исследование")
                console.print()
                continue
            
            if command.lower() == "agents":
                display_agents()
                continue
            
            if command.lower().startswith("agent "):
                new_agent = command[6:].strip()
                if new_agent in AGENTS:
                    current_agent = new_agent
                    console.print(f"[green]Переключились на агента:[/green] {new_agent}")
                else:
                    console.print(f"[red]Неизвестный агент:[/red] {new_agent}")
                    display_agents()
                continue
            
            # Выполнить исследование
            await run_agent(current_agent, command)
            console.print()
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Прервано пользователем[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[red]Ошибка:[/red] {e}")


def main():
    """Главная функция CLI."""
    parser = argparse.ArgumentParser(
        description="SGR Deep Research CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  # Интерактивный режим
  uv run python -m sgr_deep_research.cli

  # Быстрый запрос
  uv run python -m sgr_deep_research.cli --query "Что такое квантовые компьютеры?"

  # Использование конкретного агента
  uv run python -m sgr_deep_research.cli --agent sgr-tools --query "Последние новости AI"

  # Сохранение результата в файл
  uv run python -m sgr_deep_research.cli --query "Python async/await" --output report.md

  # Показать доступных агентов
  uv run python -m sgr_deep_research.cli --list-agents
        """
    )
    
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Запрос для исследования"
    )
    
    parser.add_argument(
        "--agent", "-a",
        type=str,
        choices=list(AGENTS.keys()),
        default="sgr-tools",
        help="Тип агента (по умолчанию: sgr-tools)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Файл для сохранения результата (Markdown)"
    )
    
    parser.add_argument(
        "--list-agents",
        action="store_true",
        help="Показать доступных агентов"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Включить отладочный вывод"
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Запустить в интерактивном режиме"
    )
    
    args = parser.parse_args()
    
    setup_logging(args.debug)
    
    try:
        # Проверка конфигурации
        config = get_config()
        console.print(f"[dim]Конфигурация загружена: {config.tavily.api_base_url}[/dim]")
    except Exception as e:
        console.print(f"[red]Ошибка конфигурации:[/red] {e}")
        sys.exit(1)
    
    if args.list_agents:
        display_agents()
        return
    
    if args.interactive or not args.query:
        asyncio.run(interactive_mode())
        return
    
    # Выполнить одиночный запрос
    asyncio.run(run_agent(args.agent, args.query, args.output))


if __name__ == "__main__":
    main()