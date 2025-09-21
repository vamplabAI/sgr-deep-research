"""Advanced job monitoring and management CLI commands.

This module provides enhanced CLI commands for monitoring jobs,
viewing detailed status, and managing job workflows.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import click
import httpx
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.align import Align

console = Console()


@click.group()
def monitor():
    """Advanced job monitoring commands."""
    pass


@monitor.command('dashboard')
@click.option('--refresh', '-r', type=int, default=5, help='Refresh interval in seconds')
@click.option('--limit', '-l', type=int, default=20, help='Number of jobs to display')
def job_dashboard(refresh: int, limit: int):
    """Live dashboard showing job status and progress."""
    asyncio.run(run_job_dashboard(refresh, limit))


@monitor.command('watch')
@click.argument('job_id')
@click.option('--refresh', '-r', type=int, default=2, help='Refresh interval in seconds')
def watch_job(job_id: str, refresh: int):
    """Watch a specific job with live updates."""
    asyncio.run(run_job_watch(job_id, refresh))


@monitor.command('history')
@click.option('--days', '-d', type=int, default=7, help='Number of days to show')
@click.option('--status', '-s', help='Filter by status')
@click.option('--limit', '-l', type=int, default=50, help='Maximum number of jobs')
def job_history(days: int, status: str, limit: int):
    """Show job execution history."""
    asyncio.run(run_job_history(days, status, limit))


@monitor.command('stats')
@click.option('--days', '-d', type=int, default=30, help='Number of days for statistics')
def job_stats(days: int):
    """Show job execution statistics."""
    asyncio.run(run_job_stats(days))


@monitor.command('export')
@click.argument('job_id')
@click.option('--format', '-f', type=click.Choice(['json', 'markdown', 'text']), default='json')
@click.option('--output', '-o', help='Output file path')
def export_job(job_id: str, format: str, output: str):
    """Export job results to file."""
    asyncio.run(run_export_job(job_id, format, output))


async def run_job_dashboard(refresh: int, limit: int):
    """Run the live job dashboard."""
    layout = Layout()

    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3)
    )

    layout["main"].split_row(
        Layout(name="jobs", ratio=2),
        Layout(name="details", ratio=1)
    )

    try:
        with Live(layout, refresh_per_second=1/refresh, screen=True):
            while True:
                # Update header
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                layout["header"].update(
                    Panel(
                        Align.center(f"🔄 SGR Deep Research Job Dashboard - {current_time}"),
                        style="bold blue"
                    )
                )

                # Get job data
                jobs_data = await fetch_jobs_data(limit)

                if jobs_data:
                    # Update jobs table
                    jobs_table = create_jobs_table(jobs_data.get('jobs', []))
                    layout["jobs"].update(Panel(jobs_table, title="Active Jobs", border_style="green"))

                    # Update summary
                    summary = create_job_summary(jobs_data.get('jobs', []))
                    layout["details"].update(Panel(summary, title="Summary", border_style="blue"))
                else:
                    layout["jobs"].update(Panel("❌ Unable to fetch job data", style="red"))
                    layout["details"].update(Panel("❌ No data available", style="red"))

                # Update footer
                layout["footer"].update(
                    Panel(
                        Align.center("Press Ctrl+C to exit • Refreshing every {refresh}s"),
                        style="dim"
                    )
                )

                await asyncio.sleep(refresh)

    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard stopped by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error running dashboard: {e}[/red]")


async def run_job_watch(job_id: str, refresh: int):
    """Watch a specific job with live updates."""
    console.print(f"[cyan]Watching job {job_id}...[/cyan]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    try:
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeRemainingColumn(),
            console=console,
        ) as progress:

            task = progress.add_task("Initializing...", total=100)

            while True:
                job_data = await fetch_job_data(job_id)

                if job_data:
                    status = job_data.get('status', 'unknown')
                    progress_pct = job_data.get('progress', 0.0)
                    current_step = job_data.get('current_step', 'N/A')

                    progress.update(
                        task,
                        completed=progress_pct,
                        description=f"[{status}] {current_step}"
                    )

                    # Show additional details below progress bar
                    details = f"Steps: {job_data.get('steps_completed', 0)}/{job_data.get('total_steps', 0)}"
                    if job_data.get('sources_found'):
                        details += f" | Sources: {job_data['sources_found']}"

                    console.print(f"\r{details}", end="")

                    if status in ['completed', 'failed', 'cancelled']:
                        console.print(f"\n[green]Job {status}![/green]")

                        if status == 'completed' and job_data.get('result'):
                            result = job_data['result']
                            console.print(f"\n[bold green]Results:[/bold green]")
                            console.print(f"  Sources found: {len(result.get('sources', []))}")
                            if result.get('metrics'):
                                metrics = result['metrics']
                                console.print(f"  Duration: {metrics.get('total_duration_seconds', 0):.1f}s")
                                console.print(f"  Cost: ${metrics.get('estimated_cost_usd', 0):.2f}")

                        break
                else:
                    console.print(f"\n[red]Job {job_id} not found[/red]")
                    break

                await asyncio.sleep(refresh)

    except KeyboardInterrupt:
        console.print("\n[yellow]Watch stopped by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error watching job: {e}[/red]")


async def run_job_history(days: int, status: str, limit: int):
    """Show job execution history."""
    console.print(f"[cyan]Job History (last {days} days)[/cyan]\n")

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

                # Filter by date
                cutoff_date = datetime.now() - timedelta(days=days)
                filtered_jobs = []

                for job in jobs:
                    try:
                        created_at = datetime.fromisoformat(job['created_at'].replace('Z', '+00:00'))
                        if created_at.replace(tzinfo=None) >= cutoff_date:
                            filtered_jobs.append(job)
                    except (ValueError, KeyError):
                        continue

                if not filtered_jobs:
                    console.print("[yellow]No jobs found in the specified time range[/yellow]")
                    return

                # Create detailed table
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Job ID", style="cyan", width=12)
                table.add_column("Status", justify="center", width=10)
                table.add_column("Progress", justify="center", width=8)
                table.add_column("Query", width=40)
                table.add_column("Created", width=16)
                table.add_column("Duration", width=10)

                for job in filtered_jobs:
                    status_style = {
                        'pending': 'yellow',
                        'running': 'blue',
                        'completed': 'green',
                        'failed': 'red',
                        'cancelled': 'dim'
                    }.get(job['status'], 'white')

                    # Calculate duration if completed
                    duration = "N/A"
                    if job.get('completed_at') and job.get('created_at'):
                        try:
                            created = datetime.fromisoformat(job['created_at'].replace('Z', '+00:00'))
                            completed = datetime.fromisoformat(job['completed_at'].replace('Z', '+00:00'))
                            duration_sec = (completed - created).total_seconds()
                            duration = f"{duration_sec:.0f}s"
                        except ValueError:
                            pass

                    table.add_row(
                        job['job_id'][:12],
                        f"[{status_style}]{job['status']}[/{status_style}]",
                        f"{job['progress']:.1f}%",
                        job.get('query', 'N/A')[:38] + ("..." if len(job.get('query', '')) > 38 else ""),
                        job['created_at'][:16],
                        duration
                    )

                console.print(table)
                console.print(f"\n[dim]Showing {len(filtered_jobs)} jobs from last {days} days[/dim]")

            else:
                console.print(f"[red]Error fetching job history: {response.status_code}[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


async def run_job_stats(days: int):
    """Show job execution statistics."""
    console.print(f"[cyan]Job Statistics (last {days} days)[/cyan]\n")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8010/jobs",
                params={"limit": 1000},  # Get more jobs for stats
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()
                jobs = data.get('jobs', [])

                # Filter by date and calculate stats
                cutoff_date = datetime.now() - timedelta(days=days)
                stats = {
                    'total': 0,
                    'completed': 0,
                    'failed': 0,
                    'cancelled': 0,
                    'running': 0,
                    'pending': 0,
                    'total_duration': 0,
                    'total_cost': 0,
                    'avg_duration': 0,
                    'success_rate': 0
                }

                for job in jobs:
                    try:
                        created_at = datetime.fromisoformat(job['created_at'].replace('Z', '+00:00'))
                        if created_at.replace(tzinfo=None) >= cutoff_date:
                            stats['total'] += 1
                            stats[job['status']] += 1

                            # Calculate duration and cost for completed jobs
                            if job['status'] == 'completed' and job.get('completed_at'):
                                completed_at = datetime.fromisoformat(job['completed_at'].replace('Z', '+00:00'))
                                duration = (completed_at - created_at).total_seconds()
                                stats['total_duration'] += duration

                    except (ValueError, KeyError):
                        continue

                # Calculate derived stats
                if stats['total'] > 0:
                    stats['success_rate'] = (stats['completed'] / stats['total']) * 100

                if stats['completed'] > 0:
                    stats['avg_duration'] = stats['total_duration'] / stats['completed']

                # Display stats table
                table = Table(show_header=True, header_style="bold magenta", title="Job Statistics")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green")

                table.add_row("Total Jobs", str(stats['total']))
                table.add_row("Completed", f"{stats['completed']} ({stats['completed']/max(stats['total'], 1)*100:.1f}%)")
                table.add_row("Failed", f"{stats['failed']} ({stats['failed']/max(stats['total'], 1)*100:.1f}%)")
                table.add_row("Cancelled", f"{stats['cancelled']} ({stats['cancelled']/max(stats['total'], 1)*100:.1f}%)")
                table.add_row("Currently Running", str(stats['running']))
                table.add_row("Pending", str(stats['pending']))
                table.add_row("Success Rate", f"{stats['success_rate']:.1f}%")
                table.add_row("Average Duration", f"{stats['avg_duration']:.1f}s")

                console.print(table)

            else:
                console.print(f"[red]Error fetching job data: {response.status_code}[/red]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


async def run_export_job(job_id: str, format: str, output: str):
    """Export job results to file."""
    console.print(f"[cyan]Exporting job {job_id} in {format} format...[/cyan]")

    try:
        job_data = await fetch_job_data(job_id)

        if not job_data:
            console.print(f"[red]Job {job_id} not found[/red]")
            return

        # Generate filename if not provided
        if not output:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = f"job_{job_id[:8]}_{timestamp}.{format}"

        # Export based on format
        if format == 'json':
            with open(output, 'w') as f:
                json.dump(job_data, f, indent=2, default=str)

        elif format == 'markdown':
            with open(output, 'w') as f:
                f.write(format_job_as_markdown(job_data))

        elif format == 'text':
            with open(output, 'w') as f:
                f.write(format_job_as_text(job_data))

        console.print(f"[green]✓[/green] Job exported to {output}")

    except Exception as e:
        console.print(f"[red]Error exporting job: {e}[/red]")


async def fetch_jobs_data(limit: int) -> Optional[Dict[str, Any]]:
    """Fetch jobs data from API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8010/jobs",
                params={"limit": limit},
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()

    except Exception:
        pass

    return None


async def fetch_job_data(job_id: str) -> Optional[Dict[str, Any]]:
    """Fetch single job data from API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://localhost:8010/jobs/{job_id}",
                timeout=10.0
            )

            if response.status_code == 200:
                return response.json()

    except Exception:
        pass

    return None


def create_jobs_table(jobs: List[Dict[str, Any]]) -> Table:
    """Create a rich table for jobs display."""
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("ID", width=12)
    table.add_column("Status", width=10, justify="center")
    table.add_column("Progress", width=8, justify="center")
    table.add_column("Query", width=30)
    table.add_column("Created", width=12)

    for job in jobs:
        status_style = {
            'pending': 'yellow',
            'running': 'blue',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'dim'
        }.get(job['status'], 'white')

        table.add_row(
            job['job_id'][:12],
            f"[{status_style}]{job['status']}[/{status_style}]",
            f"{job['progress']:.1f}%",
            job.get('query', 'N/A')[:28] + ("..." if len(job.get('query', '')) > 28 else ""),
            job['created_at'][:10]
        )

    return table


def create_job_summary(jobs: List[Dict[str, Any]]) -> Text:
    """Create a summary text for jobs."""
    total = len(jobs)
    status_counts = {}

    for job in jobs:
        status = job['status']
        status_counts[status] = status_counts.get(status, 0) + 1

    summary = Text()
    summary.append(f"Total Jobs: {total}\n\n", style="bold")

    for status, count in status_counts.items():
        color = {
            'pending': 'yellow',
            'running': 'blue',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'dim'
        }.get(status, 'white')

        summary.append(f"{status.title()}: ", style="bold")
        summary.append(f"{count}\n", style=color)

    return summary


def format_job_as_markdown(job_data: Dict[str, Any]) -> str:
    """Format job data as markdown."""
    md = f"""# Job Report: {job_data['job_id']}

## Job Information
- **Status**: {job_data['status']}
- **Progress**: {job_data['progress']:.1f}%
- **Current Step**: {job_data['current_step']}
- **Created**: {job_data['created_at']}
"""

    if job_data.get('started_at'):
        md += f"- **Started**: {job_data['started_at']}\n"

    if job_data.get('completed_at'):
        md += f"- **Completed**: {job_data['completed_at']}\n"

    if job_data.get('result'):
        result = job_data['result']
        md += f"""
## Results
{result.get('final_answer', 'No answer available')}

### Sources ({len(result.get('sources', []))})
"""
        for i, source in enumerate(result.get('sources', []), 1):
            md += f"{i}. [{source.get('title', 'Untitled')}]({source.get('url', '#')})\n"

        if result.get('metrics'):
            metrics = result['metrics']
            md += f"""
### Metrics
- **Duration**: {metrics.get('total_duration_seconds', 0):.1f} seconds
- **API Calls**: {metrics.get('api_calls_made', 0)}
- **Estimated Cost**: ${metrics.get('estimated_cost_usd', 0):.2f}
"""

    if job_data.get('error'):
        error = job_data['error']
        md += f"""
## Error
- **Type**: {error['error_type']}
- **Message**: {error['error_message']}
- **Occurred**: {error['occurred_at']}
"""

    return md


def format_job_as_text(job_data: Dict[str, Any]) -> str:
    """Format job data as plain text."""
    text = f"""Job Report: {job_data['job_id']}
{'=' * 50}

Job Information:
  Status: {job_data['status']}
  Progress: {job_data['progress']:.1f}%
  Current Step: {job_data['current_step']}
  Created: {job_data['created_at']}
"""

    if job_data.get('started_at'):
        text += f"  Started: {job_data['started_at']}\n"

    if job_data.get('completed_at'):
        text += f"  Completed: {job_data['completed_at']}\n"

    if job_data.get('result'):
        result = job_data['result']
        text += f"""
Results:
{result.get('final_answer', 'No answer available')}

Sources ({len(result.get('sources', []))}):
"""
        for i, source in enumerate(result.get('sources', []), 1):
            text += f"  {i}. {source.get('title', 'Untitled')} - {source.get('url', 'No URL')}\n"

        if result.get('metrics'):
            metrics = result['metrics']
            text += f"""
Metrics:
  Duration: {metrics.get('total_duration_seconds', 0):.1f} seconds
  API Calls: {metrics.get('api_calls_made', 0)}
  Estimated Cost: ${metrics.get('estimated_cost_usd', 0):.2f}
"""

    if job_data.get('error'):
        error = job_data['error']
        text += f"""
Error:
  Type: {error['error_type']}
  Message: {error['error_message']}
  Occurred: {error['occurred_at']}
"""

    return text


if __name__ == "__main__":
    monitor()