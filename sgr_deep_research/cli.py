"""Упрощенный CLI интерфейс для SGR Deep Research агентов."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Type, Optional, List, Any

import click
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn
from rich.prompt import Prompt, Confirm
from rich.spinner import Spinner
from rich.text import Text

from sgr_deep_research.core.agents import (
    BaseAgent,
    BatchGeneratorAgent,
    SGRToolCallingResearchAgent,
    AGENTS,
    DEFAULT_AGENT,
)
from sgr_deep_research.settings import get_config
from sgr_deep_research.flows import batch_simple_flow

console = Console()


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


async def run_agent_direct(
    query: str,
    deep_level: int = 0,
    output_file: Optional[str] = None,
) -> Dict[str, Any]:
    """Выполнение агента напрямую без Prefect."""
    
    try:
        console.print(f"[bold cyan]🔍 Запуск исследования (без Prefect)[/bold cyan]")
        console.print(f"[cyan]Запрос:[/cyan] {query}")
        if deep_level > 0:
            console.print(f"[cyan]Глубина:[/cyan] {deep_level}")
        console.print()

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

        # Показываем spinner во время выполнения
        with Live(Spinner("dots", text="[yellow]Выполняется исследование...[/yellow]"), refresh_per_second=4):
            await agent.execute()

        # Обработка состояния агента
        from sgr_deep_research.core.models import AgentStatesEnum
        
        if agent._context.state == AgentStatesEnum.COMPLETED:
            # Получение результата
            final_answer = ""

            # Проверяем отчеты в папке reports
            reports_dir = Path("reports")
            if reports_dir.exists():
                report_files = list(reports_dir.glob("*.md"))
                if report_files:
                    latest_report = max(report_files, key=lambda x: x.stat().st_mtime)
                    from datetime import datetime
                    if (datetime.now().timestamp() - latest_report.stat().st_mtime) < 300:
                        try:
                            with open(latest_report, "r", encoding="utf-8") as f:
                                final_answer = f.read()
                            console.print(f"[green]📄 Найден отчет:[/green] {latest_report.name}")
                        except Exception as e:
                            console.print(f"[yellow]⚠️ Не удалось прочитать отчет:[/yellow] {e}")

            # Получаем источники и статистику
            sources = list(agent._context.sources.values())
            stats = agent.metrics.format_stats()

            # Сохраняем в файл если указан
            if output_file:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(f"# Результат исследования\n\n")
                    f.write(f"**Запрос:** {query}\n\n")
                    f.write(f"**Модель:** {agent.model_name}\n\n")
                    if deep_level > 0:
                        f.write(f"**Глубина исследования:** {deep_level}\n\n")
                    f.write("## Ответ\n\n")
                    f.write(final_answer)

                    if sources:
                        f.write("\n\n## Источники\n\n")
                        for source in sources:
                            f.write(f"{source.number}. [{source.title or 'Источник'}]({source.url})\n")
                
                console.print(f"[green]💾 Результат сохранен в:[/green] {output_path}")

            # Показываем финальный ответ в markdown если он есть
            if final_answer:
                console.print("\n[bold green]📋 Результат исследования:[/bold green]")
                console.print(Markdown(final_answer))
            
            # Создаем панель с итогами
            stats_text = f"""[green]📊 Источников найдено:[/green] {len(sources)}
[green]⏱️  Время выполнения:[/green] {stats.get('Время выполнения', 'N/A')}
[green]🔍 Поисковых запросов:[/green] {stats.get('Поисковые запросы', 'N/A')}
[green]💰 Стоимость:[/green] {stats.get('Стоимость (общая)', 'N/A')}
[green]🧠 Шагов выполнено:[/green] {stats.get('Шаги выполнения', 'N/A')}"""

            results_panel = Panel(
                stats_text,
                title="[bold green]✅ Исследование завершено![/bold green]",
                title_align="left",
                border_style="green",
                padding=(1, 2)
            )
            console.print(results_panel)
            
            # Показываем источники если их много
            if len(sources) > 0:
                sources_text = "\n".join([
                    f"[cyan]{i+1}.[/cyan] [link={source.url}]{source.title or 'Источник'}[/link]"
                    for i, source in enumerate(sources[:5])  # Показываем первые 5
                ])
                
                if len(sources) > 5:
                    sources_text += f"\n[dim]... и ещё {len(sources) - 5} источников[/dim]"
                
                sources_panel = Panel(
                    sources_text,
                    title=f"[bold blue]📚 Источники ({len(sources)})[/bold blue]",
                    title_align="left", 
                    border_style="blue",
                    padding=(1, 2)
                )
                console.print(sources_panel)
            
            return {
                "status": "COMPLETED",
                "answer": final_answer,
                "sources": [{"number": s.number, "url": s.url, "title": s.title} for s in sources],
                "stats": stats,
                "deep_level": deep_level,
            }
            
        else:
            console.print(f"[red]❌ Агент завершился с состоянием:[/red] {agent._context.state}")
            return {
                "status": "ERROR",
                "error": f"Agent finished with state: {agent._context.state}",
                "stats": agent.metrics.format_stats(),
            }
        
    except Exception as e:
        console.print(f"[red]❌ Ошибка при выполнении агента:[/red] {e}")
        import traceback
        console.print(f"[red]Traceback:[/red]\n{traceback.format_exc()}")
        return {
            "status": "ERROR",
            "error": str(e),
            "stats": {},
        }


async def run_batch_simple(
    topic: str,
    count: int = 5,
    agent_type: str = DEFAULT_AGENT,
    max_concurrent: int = 3,
    result_dir: str = "batch_results",
    deep_level: int = 0,
) -> None:
    """Выполняет упрощенное batch-исследование используя batch_simple_flow."""
    
    console.print(f"[bold cyan]🚀 Упрощенное batch исследование (с Prefect)[/bold cyan]")
    console.print(f"[cyan]Тема:[/cyan] {topic}")
    console.print(f"[cyan]Количество запросов:[/cyan] {count}")
    console.print(f"[cyan]Агент:[/cyan] {agent_type}")
    console.print(f"[cyan]Максимум параллельных задач:[/cyan] {max_concurrent}")
    if deep_level > 0:
        console.print(f"[cyan]Режим дипа:[/cyan] уровень {deep_level} (~{5 * (deep_level * 3 + 1)} шагов)")
    
    try:
        console.print("[yellow]⚡ Запускаем упрощенный Prefect flow...[/yellow]")
        
        # Запускаем упрощенный Prefect flow
        result = await batch_simple_flow(
            topic=topic,
            count=count,
            agent_type=agent_type,
            max_concurrent=max_concurrent,
            result_dir=result_dir,
            deep_level=deep_level,
        )
        
        if result.get("status") == "COMPLETED":
            console.print(f"\n[bold green]🎉 Batch исследование завершено![/bold green]")
            console.print(f"[green]✅ Успешно:[/green] {result['completed']}/{result['total_queries']}")
            if result['failed'] > 0:
                console.print(f"[red]❌ Ошибок:[/red] {result['failed']}")
            if result['exceptions'] > 0:
                console.print(f"[red]💥 Исключений:[/red] {result['exceptions']}")
            console.print(f"[green]📁 Результаты в:[/green] {result['result_dir']}")
            
            # Показываем сгенерированные запросы
            queries = result.get('queries', [])
            if queries:
                console.print(f"\n[bold blue]📝 Сгенерированные запросы ({len(queries)}):[/bold blue]")
                for i, query in enumerate(queries[:10], 1):  # Показываем первые 10
                    console.print(f"  [cyan]{i:2d}.[/cyan] {query.get('query', 'N/A')}")
                if len(queries) > 10:
                    console.print(f"  [dim]... и ещё {len(queries) - 10} запросов[/dim]")
        else:
            console.print(f"[red]❌ Batch завершился с ошибкой: {result.get('error', 'Unknown error')}[/red]")
        
    except Exception as e:
        console.print(f"[red]❌ Ошибка выполнения batch:[/red] {e}")
        import traceback
        console.print(f"[red]Traceback:[/red]\n{traceback.format_exc()}")


async def interactive_mode():
    """Интерактивный режим работы."""
    console.print("[bold cyan]🔍 SGR Deep Research - Интерактивный режим[/bold cyan]")
    console.print("Введите 'help' для справки, 'quit' для выхода\n")
    
    current_agent = DEFAULT_AGENT
    
    while True:
        try:
            command = Prompt.ask(f"[{current_agent}]", default="").strip()
            
            if not command or command.lower() in ["quit", "exit", "q"]:
                console.print("[yellow]До свидания![/yellow]")
                break
            
            if command.lower() == "help":
                console.print("\n[bold cyan]Команды:[/bold cyan]")
                console.print("  help                    - Показать эту справку")
                console.print("  agents                  - Показать доступных агентов")
                console.print("  agent <type>            - Переключиться на агента")
                console.print("  deep <уровень> <запрос> - Глубокое исследование (уровни 1-5+)")
                console.print("  batch <тема>            - Batch исследование (Prefect)")
                console.print("  batch-deep <уровень> <тема> - Batch с глубоким исследованием")
                console.print("  quit/exit/q             - Выйти")
                console.print("  <ваш запрос>            - Обычное исследование\n")
                continue
            
            if command.lower() == "agents":
                display_agents()
                continue
            
            if command.lower().startswith("agent "):
                agent_name = command[6:].strip()
                if agent_name in AGENTS:
                    current_agent = agent_name
                    console.print(f"[green]✅ Переключились на агента:[/green] {agent_name}")
                else:
                    console.print(f"[red]❌ Неизвестный агент:[/red] {agent_name}")
                    console.print("Доступные агенты:")
                    display_agents()
                continue
            
            if command.lower().startswith("deep "):
                parts = command[5:].strip().split(maxsplit=1)
                if len(parts) == 2:
                    try:
                        level = int(parts[0])
                        query = parts[1]
                        await run_agent_direct(query, level)
                    except ValueError:
                        console.print("[red]❌ Неверный уровень глубины. Используйте число.[/red]")
                else:
                    console.print("[red]❌ Использование: deep <уровень> <запрос>[/red]")
                continue
            
            if command.lower().startswith("batch "):
                topic = command[6:].strip()
                if topic:
                    await run_batch_simple(topic, count=5, agent_type=current_agent)
                else:
                    console.print("[red]❌ Использование: batch <тема>[/red]")
                continue
            
            if command.lower().startswith("batch-deep "):
                parts = command[11:].strip().split(maxsplit=1)
                if len(parts) == 2:
                    try:
                        level = int(parts[0])
                        topic = parts[1]
                        await run_batch_simple(topic, count=5, agent_type=current_agent, deep_level=level)
                    except ValueError:
                        console.print("[red]❌ Неверный уровень глубины. Используйте число.[/red]")
                else:
                    console.print("[red]❌ Использование: batch-deep <уровень> <тема>[/red]")
                continue
            
            # Обычный запрос
            await run_agent_direct(command)
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Прервано пользователем[/yellow]")
            continue
        except Exception as e:
            console.print(f"[red]❌ Ошибка:[/red] {e}")


@click.group(invoke_without_command=True)
@click.option('--query', '-q', help='Запрос для исследования')
@click.option('--agent', '-a', 
              type=click.Choice(list(AGENTS.keys())), 
              default=DEFAULT_AGENT,
              help='Тип агента')
@click.option('--output', '-o', help='Файл для сохранения результата')
@click.option('--deep', '-d', type=int, default=0, help='Уровень глубины исследования (0-5+)')
@click.option('--debug', is_flag=True, help='Режим отладки')
@click.option('--interactive', '-i', is_flag=True, help='Интерактивный режим')
@click.pass_context
def cli(ctx, query, agent, output, deep, debug, interactive):
    """SGR Deep Research CLI - Упрощенная версия.
    
    Режимы работы:
    1. Сингл режим (без Prefect) - прямое выполнение агента
    2. Batch режим (с Prefect) - множественные запросы через Prefect flow
    3. Deep режимы - глубокое исследование с разными уровнями
    """
    
    # Настройка логирования
    setup_logging(debug)
    
    # Проверяем конфигурацию
    try:
        config = get_config()
    except Exception as e:
        console.print(f"[red]Ошибка конфигурации:[/red] {e}")
        sys.exit(1)
    
    # Если команда не вызвана, запускаем основную логику
    if ctx.invoked_subcommand is None:
        if interactive or not query:
            asyncio.run(interactive_mode())
        else:
            # Выполнить одиночный запрос напрямую (без Prefect)
            asyncio.run(run_agent_direct(query, deep, output))


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
    """Глубокое исследование (без Prefect).
    
    Уровни глубины:
    1 - ~20 шагов, 10-30 мин
    2 - ~40 шагов, 20-60 мин  
    3 - ~60 шагов, 30-90 мин
    4+ - ~80+ шагов, 40+ мин
    """
    asyncio.run(run_agent_direct(query, level, output))


@cli.command()
@click.argument('topic')
@click.option('--count', '-c', type=int, default=5, help='Количество запросов для генерации')
@click.option('--agent', '-a', 
              type=click.Choice(list(AGENTS.keys())), 
              default='sgr-tools',
              help='Тип агента')
@click.option('--concurrent', '-j', type=int, default=3, help='Максимум параллельных задач')
@click.option('--output-dir', '-o', default='batch_results', help='Папка для результатов')
@click.option('--deep', '-d', type=int, default=0, help='Уровень глубины исследования (0-5+, 0=обычный режим)')
def batch(topic, count, agent, concurrent, output_dir, deep):
    """Батч исследование - множественные запросы по теме (с Prefect).
    
    Примеры:
        uv run python -m sgr_deep_research.cli batch "современные AI технологии"
        uv run python -m sgr_deep_research.cli batch "история башкир" --count 10 --concurrent 2
        uv run python -m sgr_deep_research.cli batch "AI research" --deep 2 --count 3
    """
    asyncio.run(run_batch_simple(topic, count, agent, concurrent, output_dir, deep))


# Job Management Commands

@cli.group()
def jobs():
    """Job management commands."""
    pass


@jobs.command('submit')
@click.argument('query')
@click.option('--agent', '-a', default='sgr-tools', help='Agent type (sgr, sgr-tools, etc.)')
@click.option('--deep', '-d', type=int, default=0, help='Deep research level (0-5+)')
@click.option('--priority', '-p', type=int, default=0, help='Job priority (-100 to 100)')
@click.option('--tags', '-t', help='Comma-separated tags')
def submit_job(query, agent, deep, priority, tags):
    """Submit a new research job."""
    asyncio.run(submit_job_cmd(query, agent, deep, priority, tags))


@jobs.command('status')
@click.argument('job_id')
def job_status(job_id):
    """Get job status."""
    asyncio.run(get_job_status_cmd(job_id))


@jobs.command('list')
@click.option('--status', '-s', help='Filter by status (pending, running, completed, failed, cancelled)')
@click.option('--limit', '-l', type=int, default=20, help='Maximum number of jobs to show')
def list_jobs(status, limit):
    """List jobs."""
    asyncio.run(list_jobs_cmd(status, limit))


@jobs.command('cancel')
@click.argument('job_id')
def cancel_job(job_id):
    """Cancel a job."""
    asyncio.run(cancel_job_cmd(job_id))


@jobs.command('stream')
@click.argument('job_id')
def stream_job(job_id):
    """Stream job progress updates."""
    asyncio.run(stream_job_cmd(job_id))


async def submit_job_cmd(query: str, agent: str, deep: int, priority: int, tags: str):
    """Submit a job command implementation."""
    import httpx
    from sgr_deep_research.settings import get_config

    config = get_config()

    # Prepare request data
    request_data = {
        "query": query,
        "agent_type": agent,
        "deep_level": deep,
        "priority": priority,
        "tags": tags.split(",") if tags else [],
        "metadata": {}
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8010/jobs",
                json=request_data,
                timeout=30.0
            )

            if response.status_code == 201:
                data = response.json()
                console.print(f"[green]✓[/green] Job submitted successfully!")
                console.print(f"  Job ID: [cyan]{data['job_id']}[/cyan]")
                console.print(f"  Status: [yellow]{data['status']}[/yellow]")
                console.print(f"  Created: [blue]{data['created_at']}[/blue]")
                if data.get('estimated_completion'):
                    console.print(f"  Estimated completion: [blue]{data['estimated_completion']}[/blue]")
            else:
                console.print(f"[red]✗[/red] Failed to submit job: {response.status_code}")
                console.print(response.text)

    except Exception as e:
        console.print(f"[red]✗[/red] Error submitting job: {e}")


async def get_job_status_cmd(job_id: str):
    """Get job status command implementation."""
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://localhost:8010/jobs/{job_id}",
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                console.print(f"\n[bold cyan]Job Status: {job_id}[/bold cyan]")
                console.print(f"  Status: [yellow]{data['status']}[/yellow]")
                console.print(f"  Progress: [green]{data['progress']:.1f}%[/green]")
                console.print(f"  Current step: {data['current_step']}")
                console.print(f"  Steps completed: {data['steps_completed']}/{data['total_steps']}")
                console.print(f"  Created: [blue]{data['created_at']}[/blue]")

                if data.get('started_at'):
                    console.print(f"  Started: [blue]{data['started_at']}[/blue]")

                if data.get('completed_at'):
                    console.print(f"  Completed: [blue]{data['completed_at']}[/blue]")

                if data.get('result'):
                    result = data['result']
                    console.print(f"\n[bold green]Results:[/bold green]")
                    console.print(f"  Sources found: {len(result.get('sources', []))}")
                    if result.get('metrics'):
                        metrics = result['metrics']
                        console.print(f"  Duration: {metrics.get('total_duration_seconds', 0):.1f}s")
                        console.print(f"  API calls: {metrics.get('api_calls_made', 0)}")
                        console.print(f"  Estimated cost: ${metrics.get('estimated_cost_usd', 0):.2f}")

                if data.get('error'):
                    error = data['error']
                    console.print(f"\n[bold red]Error:[/bold red]")
                    console.print(f"  Type: {error['error_type']}")
                    console.print(f"  Message: {error['error_message']}")
                    console.print(f"  Occurred: [blue]{error['occurred_at']}[/blue]")

            elif response.status_code == 404:
                console.print(f"[red]✗[/red] Job not found: {job_id}")
            else:
                console.print(f"[red]✗[/red] Error getting job status: {response.status_code}")
                console.print(response.text)

    except Exception as e:
        console.print(f"[red]✗[/red] Error getting job status: {e}")


async def list_jobs_cmd(status: str, limit: int):
    """List jobs command implementation."""
    import httpx

    try:
        params = {"limit": limit}
        if status:
            params["status"] = status

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8010/jobs",
                params=params,
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                jobs = data.get('jobs', [])

                if not jobs:
                    console.print("[yellow]No jobs found[/yellow]")
                    return

                console.print(f"\n[bold cyan]Jobs (showing {len(jobs)} of {data.get('total', len(jobs))})[/bold cyan]")

                for job in jobs:
                    status_color = {
                        'pending': 'yellow',
                        'running': 'blue',
                        'completed': 'green',
                        'failed': 'red',
                        'cancelled': 'gray'
                    }.get(job['status'], 'white')

                    console.print(f"  [{status_color}]{job['job_id']}[/{status_color}] - {job['status']} ({job['progress']:.1f}%)")
                    console.print(f"    Query: {job.get('query', 'N/A')}")
                    console.print(f"    Created: [blue]{job['created_at']}[/blue]")

            else:
                console.print(f"[red]✗[/red] Error listing jobs: {response.status_code}")
                console.print(response.text)

    except Exception as e:
        console.print(f"[red]✗[/red] Error listing jobs: {e}")


async def cancel_job_cmd(job_id: str):
    """Cancel job command implementation."""
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"http://localhost:8010/jobs/{job_id}",
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                console.print(f"[green]✓[/green] Job cancelled successfully!")
                console.print(f"  Job ID: [cyan]{data['job_id']}[/cyan]")
                console.print(f"  Status: [yellow]{data['status']}[/yellow]")
                console.print(f"  Cancelled at: [blue]{data['cancelled_at']}[/blue]")
            elif response.status_code == 404:
                console.print(f"[red]✗[/red] Job not found: {job_id}")
            elif response.status_code == 409:
                console.print(f"[red]✗[/red] Job cannot be cancelled (already completed)")
            else:
                console.print(f"[red]✗[/red] Error cancelling job: {response.status_code}")
                console.print(response.text)

    except Exception as e:
        console.print(f"[red]✗[/red] Error cancelling job: {e}")


async def stream_job_cmd(job_id: str):
    """Stream job progress command implementation."""
    import httpx

    console.print(f"[cyan]Streaming updates for job {job_id}...[/cyan]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "GET",
                f"http://localhost:8010/jobs/{job_id}/stream",
                timeout=300.0
            ) as response:

                if response.status_code != 200:
                    console.print(f"[red]✗[/red] Error starting stream: {response.status_code}")
                    return

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            import json
                            data = json.loads(line[6:])  # Remove "data: " prefix

                            if 'error' in data:
                                console.print(f"[red]Error: {data['error']}[/red]")
                                break

                            console.print(f"[{data.get('status', 'unknown')}] {data.get('progress', 0):.1f}% - {data.get('current_step', 'N/A')}")

                            if data.get('status') in ['completed', 'failed', 'cancelled']:
                                console.print(f"[green]Stream ended: Job {data['status']}[/green]")
                                break

                        except json.JSONDecodeError:
                            continue  # Skip invalid JSON lines

    except KeyboardInterrupt:
        console.print("\n[yellow]Stream stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]✗[/red] Error streaming job updates: {e}")


def main():
    """Точка входа CLI."""
    cli()


if __name__ == "__main__":
    main()