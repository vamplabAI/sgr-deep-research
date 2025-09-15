"""CLI интерфейс для SGR Deep Research агентов."""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Type

import click
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


async def run_agent(agent_type: str, query: str, output_file: str = None, deep_level: int = 0):
    """Запустить агента с заданным запросом."""
    if agent_type not in AGENTS:
        console.print(f"[red]Ошибка:[/red] Неизвестный тип агента '{agent_type}'")
        display_agents()
        return

    agent_class = AGENTS[agent_type]
    
    try:
        console.print(f"\n[bold cyan]Инициализация агента:[/bold cyan] {agent_class.__name__}")
        
        # Настройка глубокого режима - простое масштабирование параметров
        if deep_level > 0:
            # Базовые значения
            base_steps = 6
            base_searches = 4
            
            # Динамическое масштабирование
            max_iterations = base_steps * (deep_level * 3 + 1)  # 6 -> 12/24/36/48
            max_searches = base_searches * (deep_level + 1)     # 4 -> 8/12/16/20
            
            # Создаем агента с увеличенными параметрами
            if hasattr(agent_class, '__init__'):
                import inspect
                sig = inspect.signature(agent_class.__init__)
                kwargs = {'task': query}
                
                if 'max_iterations' in sig.parameters:
                    kwargs['max_iterations'] = max_iterations
                if 'max_searches' in sig.parameters:
                    kwargs['max_searches'] = max_searches
                
                agent = agent_class(**kwargs)
            else:
                agent = agent_class(query, max_iterations=max_iterations)
            
            console.print(f"[bold yellow]🔍 ГЛУБОКИЙ РЕЖИМ УРОВНЯ {deep_level}[/bold yellow]")
            console.print(f"[yellow]Максимум шагов: {max_iterations}[/yellow]")
            console.print(f"[yellow]Максимум поисков: {max_searches}[/yellow]")
            console.print(f"[yellow]Примерное время: {deep_level * 10}-{deep_level * 30} минут[/yellow]")
            
            # Устанавливаем deep_level для использования в параметрах модели
            agent._deep_level = deep_level
            
            # Проверяем поддержку GPT-5
            if hasattr(agent, '_get_model_parameters'):
                model_params = agent._get_model_parameters(deep_level)
                if 'max_completion_tokens' in model_params:
                    console.print(f"[dim]GPT-5 режим: {model_params['max_completion_tokens']} токенов, reasoning_effort={model_params.get('reasoning_effort', 'medium')}[/dim]")
                else:
                    console.print(f"[dim]Контекст: {model_params['max_tokens']} токенов[/dim]")
        else:
            agent = agent_class(query)
        
        console.print(f"[bold cyan]Запрос:[/bold cyan] {query}")
        console.print(f"[bold cyan]Модель:[/bold cyan] {agent.model_name}")
        console.print()
        
        # Запуск агента с интерактивной обработкой уточнений
        from sgr_deep_research.core.models import AgentStatesEnum
        
        # Запуск агента в фоновом режиме
        agent_task = asyncio.create_task(agent.execute())
        
        # Мониторинг состояния агента
        while agent._context.state not in AgentStatesEnum.FINISH_STATES.value:
            if agent._context.state == AgentStatesEnum.WAITING_FOR_CLARIFICATION:
                # Агент ждет уточнений
                console.print("\n[bold yellow]🤔 Агент запрашивает уточнения:[/bold yellow]")
                
                # Получаем последний результат инструмента clarification
                last_clarification = ""
                if agent.log:
                    for log_entry in reversed(agent.log):
                        if (log_entry.get("step_type") == "tool_execution" and 
                            log_entry.get("tool_name") == "clarificationtool"):
                            last_clarification = log_entry.get("agent_tool_execution_result", "")
                            break
                
                if last_clarification:
                    console.print(Panel(last_clarification, title="Вопросы", border_style="yellow"))
                
                # Запрашиваем ответ от пользователя
                user_answer = Prompt.ask("\n[bold]Ваш ответ[/bold]", default="")
                
                if user_answer.strip():
                    # Передаем уточнения агенту
                    await agent.provide_clarification(user_answer)
                    console.print("[green]✅ Уточнения переданы агенту[/green]\n")
                else:
                    # Пользователь не ответил, завершаем
                    console.print("[yellow]⚠️ Нет ответа, завершаем работу агента[/yellow]")
                    break
            
            await asyncio.sleep(0.1)
        
        # Ждем завершения задачи агента
        try:
            await agent_task
        except asyncio.CancelledError:
            pass
        
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
            
            # Отображение статистики выполнения
            console.print(f"\n[bold yellow]📊 Статистика выполнения:[/bold yellow]")
            stats = agent.metrics.format_stats()
            for key, value in stats.items():
                console.print(f"  [cyan]{key}:[/cyan] {value}")
            
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
            
            # Отображение статистики даже при ошибке
            console.print(f"\n[bold yellow]📊 Статистика выполнения:[/bold yellow]")
            stats = agent.metrics.format_stats()
            for key, value in stats.items():
                console.print(f"  [cyan]{key}:[/cyan] {value}")
            
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
                console.print("  deep <запрос>     - Глубокое исследование (20 шагов)")
                console.print("  deep2 <запрос>    - Очень глубокое (40 шагов, ~20-60 мин)")
                console.print("  deep3 <запрос>    - Экстремально глубокое (60 шагов, ~30-90 мин)")
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
            deep_level = 0
            if command.startswith("deep"):
                if command.startswith("deep "):
                    deep_level = 1
                    command = command[5:]  # Убрать "deep " из начала
                else:
                    # Проверяем паттерн deep1, deep2, deep3 и т.д.
                    import re
                    match = re.match(r"deep(\d+)\s+(.+)", command)
                    if match:
                        deep_level = int(match.group(1))
                        command = match.group(2)
                    else:
                        # Проверяем просто deep1, deep2 без пробела
                        match = re.match(r"deep(\d+)$", command.split()[0])
                        if match and len(command.split()) > 1:
                            deep_level = int(match.group(1))
                            command = " ".join(command.split()[1:])
                
                if deep_level > 0:
                    console.print(f"[yellow]🔍 Глубокий режим уровня {deep_level} (время: ~{deep_level * 10}-{deep_level * 30} мин)[/yellow]")
            
            await run_agent(current_agent, command, deep_level=deep_level)
            console.print()
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Прервано пользователем[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[red]Ошибка:[/red] {e}")


@click.group(invoke_without_command=True)
@click.option('--query', '-q', help='Запрос для исследования')
@click.option('--agent', '-a', 
              type=click.Choice(list(AGENTS.keys())), 
              default='sgr-tools',
              help='Тип агента (по умолчанию: sgr-tools)')
@click.option('--output', '-o', help='Файл для сохранения результата (Markdown)')
@click.option('--deep', type=int, default=0, 
              help='Уровень глубокого исследования (1-5+: 1=20 шагов, 2=40 шагов, 3=60 шагов...)')
@click.option('--debug', is_flag=True, help='Включить отладочный вывод')
@click.option('--interactive', '-i', is_flag=True, help='Запустить в интерактивном режиме')
@click.pass_context
def cli(ctx, query, agent, output, deep, debug, interactive):
    """SGR Deep Research CLI
    
    Примеры использования:
    
      # Интерактивный режим
      uv run python -m sgr_deep_research.cli
    
      # Быстрый запрос
      uv run python -m sgr_deep_research.cli --query "Что такое квантовые компьютеры?"
    
      # Использование конкретного агента
      uv run python -m sgr_deep_research.cli --agent sgr-tools --query "Последние новости AI"
    
      # Сохранение результата в файл
      uv run python -m sgr_deep_research.cli --query "Python async/await" --output report.md
    """
    setup_logging(debug)
    
    try:
        # Проверка конфигурации
        config = get_config()
        console.print(f"[dim]Конфигурация загружена: {config.tavily.api_base_url}[/dim]")
    except Exception as e:
        console.print(f"[red]Ошибка конфигурации:[/red] {e}")
        sys.exit(1)
    
    # Если команда не вызвана, запускаем основную логику
    if ctx.invoked_subcommand is None:
        if interactive or not query:
            asyncio.run(interactive_mode())
        else:
            # Выполнить одиночный запрос
            asyncio.run(run_agent(agent, query, output, deep))


@cli.command()
def agents():
    """Показать доступных агентов."""
    display_agents()


@cli.command()
@click.argument('query')
@click.option('--level', '-l', type=int, default=1, help='Уровень глубины (1-5+)')
@click.option('--agent', '-a', 
              type=click.Choice(list(AGENTS.keys())), 
              default='sgr-tools',
              help='Тип агента')
@click.option('--output', '-o', help='Файл для сохранения результата')
def deep(query, level, agent, output):
    """Глубокое исследование с указанным уровнем."""
    asyncio.run(run_agent(agent, query, output, level))


@cli.command()
@click.argument('query')
@click.option('--agent', '-a', 
              type=click.Choice(list(AGENTS.keys())), 
              default='sgr-tools',
              help='Тип агента')
@click.option('--output', '-o', help='Файл для сохранения результата')
def deep1(query, agent, output):
    """Глубокое исследование уровня 1 (20 шагов, ~10-30 мин)."""
    asyncio.run(run_agent(agent, query, output, 1))


@cli.command()
@click.argument('query')
@click.option('--agent', '-a', 
              type=click.Choice(list(AGENTS.keys())), 
              default='sgr-tools',
              help='Тип агента')
@click.option('--output', '-o', help='Файл для сохранения результата')
def deep2(query, agent, output):
    """Очень глубокое исследование уровня 2 (40 шагов, ~20-60 мин)."""
    asyncio.run(run_agent(agent, query, output, 2))


@cli.command()
@click.argument('query')
@click.option('--agent', '-a', 
              type=click.Choice(list(AGENTS.keys())), 
              default='sgr-tools',
              help='Тип агента')
@click.option('--output', '-o', help='Файл для сохранения результата')
def deep3(query, agent, output):
    """Экстремально глубокое исследование уровня 3 (60 шагов, ~30-90 мин)."""
    asyncio.run(run_agent(agent, query, output, 3))


def main():
    """Точка входа CLI."""
    cli()


if __name__ == "__main__":
    main()