#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SGR Research Agent - Clean Architecture
Двухфазный исследовательский агент:
1. Reasoning Phase: Анализ ситуации через Structured Output
2. Action Phase: Выполнение действий через Function Calls
"""

import json
import os
import yaml
import asyncio
from typing import Any, Dict, List
from pydantic import ValidationError

from openai import OpenAI
from tavily import TavilyClient
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule

# Локальные модули
from models import (
    ReasoningStep,
    ClarificationStep,
    WebSearchStep,
    CreateReportStep,
    ReportCompletionStep,
)
from tool_schemas import get_all_tools, make_tool_choice_generate_reasoning
from executors import get_executors


# =============================================================================
# CONFIGURATION
# =============================================================================


def load_config() -> Dict[str, Any]:
    """Load configuration from environment and config file"""
    cfg = {
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "openai_base_url": os.getenv("OPENAI_BASE_URL", ""),
        "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "max_tokens": int(os.getenv("MAX_TOKENS", "6000")),
        "temperature": float(os.getenv("TEMPERATURE", "0.3")),
        "tavily_api_key": os.getenv("TAVILY_API_KEY", ""),
        "max_search_results": int(os.getenv("MAX_SEARCH_RESULTS", "10")),
        "max_rounds": int(os.getenv("MAX_ROUNDS", "8")),
        "reports_directory": os.getenv("REPORTS_DIRECTORY", "reports"),
        "max_searches_total": int(os.getenv("MAX_SEARCHES_TOTAL", "6")),
        "so_temperature": float(os.getenv("SO_TEMPERATURE", "0.1")),
    }

    if os.path.exists("config.yaml"):
        try:
            with open("config.yaml", "r", encoding="utf-8") as f:
                y = yaml.safe_load(f) or {}

            # Update from YAML config
            if "openai" in y:
                oc = y["openai"]
                cfg.update(
                    {
                        k: oc.get(k.split("_", 1)[1], v)
                        for k, v in cfg.items()
                        if k.startswith("openai_")
                    }
                )

            if "tavily" in y:
                cfg["tavily_api_key"] = y["tavily"].get(
                    "api_key", cfg["tavily_api_key"]
                )

            if "search" in y:
                cfg["max_search_results"] = y["search"].get(
                    "max_results", cfg["max_search_results"]
                )

            if "execution" in y:
                ex = y["execution"]
                cfg.update(
                    {
                        "max_rounds": ex.get("max_rounds", cfg["max_rounds"]),
                        "reports_directory": ex.get(
                            "reports_dir", cfg["reports_directory"]
                        ),
                        "max_searches_total": ex.get(
                            "max_searches_total", cfg["max_searches_total"]
                        ),
                    }
                )
        except Exception as e:
            print(f"[yellow]Warning: could not load config.yaml: {e}[/yellow]")

    return cfg


def load_prompts() -> Dict[str, Any]:
    """Load system prompts from prompts.yaml"""
    try:
        with open("prompts.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        raise RuntimeError(f"Could not load prompts.yaml: {e}")


# =============================================================================
# INITIALIZATION
# =============================================================================

console = Console()
print = console.print

CONFIG = load_config()
PROMPTS = load_prompts()

# Validate required config
if not CONFIG["openai_api_key"]:
    print("[red]ERROR: OPENAI_API_KEY is required[/red]")
    raise SystemExit(1)
if not CONFIG["tavily_api_key"]:
    print("[red]ERROR: TAVILY_API_KEY is required[/red]")
    raise SystemExit(1)

# Initialize clients
openai_kwargs = {"api_key": CONFIG["openai_api_key"]}
if CONFIG["openai_base_url"]:
    openai_kwargs["base_url"] = CONFIG["openai_base_url"]

client = OpenAI(**openai_kwargs)
tavily = TavilyClient(CONFIG["tavily_api_key"])
executors = get_executors()


# =============================================================================
# CONTEXT MANAGEMENT
# =============================================================================


def create_fresh_context() -> Dict[str, Any]:
    """Create fresh research context"""
    return {
        "searches": [],
        "sources": {},  # url -> {"number": int, "title": str, "url": str}
        "citation_counter": 0,
        "clarification_used": False,
        "searches_total": 0,
        "report_created": False,
    }


# =============================================================================
# VALIDATION
# =============================================================================


def validate_reasoning_step(rs: ReasoningStep, context: Dict[str, Any]) -> List[str]:
    """Validate reasoning step against context"""
    errors: List[str] = []

    # Anti-cycling checks
    if context.get("clarification_used", False) and rs.next_action == "clarify":
        errors.append(
            "ANTI-CYCLING: Clarification already used; repetition is forbidden."
        )

    if context.get("report_created", False) and rs.next_action == "report":
        errors.append(
            "ANTI-CYCLING: Report already created; repeated creation is forbidden."
        )

    # Search limits
    if rs.next_action == "search":
        if context.get("searches_total", 0) >= CONFIG["max_searches_total"]:
            errors.append(
                f"Search limit exceeded: already {context.get('searches_total',0)}, limit {CONFIG['max_searches_total']}."
            )

    return errors


# =============================================================================
# UI HELPERS
# =============================================================================


def pretty_print_reasoning(rs: ReasoningStep) -> None:
    """Display reasoning analysis in formatted table"""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Field")
    table.add_column("Value", overflow="fold")

    table.add_row("Current", rs.current_situation)
    table.add_row("Plan status", rs.plan_status)
    table.add_row("Reasoning steps", " • ".join(rs.reasoning_steps))
    table.add_row("Next action", f"[bold cyan]{rs.next_action}[/bold cyan]")
    table.add_row("Action reasoning", rs.action_reasoning)
    table.add_row("Remaining steps", " → ".join(rs.remaining_steps))
    table.add_row("Searches done", str(rs.searches_done))
    table.add_row("Enough data", str(rs.enough_data))
    table.add_row("Task completed", str(rs.task_completed))

    print(Panel(table, title="🧠 Reasoning Analysis", border_style="magenta"))


def build_dialog_snapshot(messages: List[Dict[str, Any]], limit: int = 30) -> str:
    """Build compact dialog summary for context"""
    tail = messages[-limit:]
    lines = []

    for m in tail:
        role = m.get("role", "")
        content = m.get("content", "")
        tool_calls = m.get("tool_calls", [])

        # Truncate long content
        if isinstance(content, str) and len(content) > 4000:
            content = content[:4000] + " …[truncated]"

        msg_parts = [f"{role.upper()}: {content}"]
        if tool_calls:
            tool_info = [
                tc.get("function", {}).get("name", "unknown") for tc in tool_calls
            ]
            msg_parts.append(f" [tools: {', '.join(tool_info)}]")

        lines.append("".join(msg_parts))

    return "\n".join(lines)


# =============================================================================
# CORE PHASES
# =============================================================================


def exec_reasoning_phase(
    messages: List[Dict[str, Any]], task: str, context: Dict[str, Any]
) -> ReasoningStep:
    """Phase 1: Get reasoning analysis from model via Structured Output"""
    print("[blue]Phase 1: Analyzing situation...[/blue]")

    # Force reasoning call
    completion = client.chat.completions.create(
        model=CONFIG["openai_model"],
        temperature=CONFIG["temperature"],
        max_tokens=CONFIG["max_tokens"],
        tools=get_all_tools(),
        tool_choice=make_tool_choice_generate_reasoning(),
        messages=messages,
    )
    msg = completion.choices[0].message

    # Validate reasoning call
    if (
        not getattr(msg, "tool_calls", None)
        or len(msg.tool_calls) != 1
        or msg.tool_calls[0].function.name != "generate_reasoning"
    ):
        raise RuntimeError("Expected exactly one 'generate_reasoning' call.")

    # Add reasoning to message log
    reasoning_call_id = msg.tool_calls[0].id
    messages.append(
        {
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {
                    "id": reasoning_call_id,
                    "type": "function",
                    "function": {"name": "generate_reasoning", "arguments": "{}"},
                }
            ],
        }
    )

    # Execute reasoning via SO call
    reasoning_result = exec_structured_output_reasoning(messages, task, context)

    # Add reasoning result to log
    messages.append(
        {
            "role": "tool",
            "tool_call_id": reasoning_call_id,
            "content": json.dumps(reasoning_result, ensure_ascii=False),
        }
    )

    if "error" in reasoning_result:
        raise RuntimeError(f"Reasoning validation failed: {reasoning_result['error']}")

    reasoning = ReasoningStep.model_validate(reasoning_result["reasoning"])
    pretty_print_reasoning(reasoning)

    return reasoning


def exec_structured_output_reasoning(
    messages: List[Dict[str, Any]], task: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Internal SO call for reasoning analysis"""
    schema = ReasoningStep.model_json_schema()
    dialog_snapshot = build_dialog_snapshot(messages, limit=30)

    so_messages = [
        {
            "role": "system",
            "content": PROMPTS["structured_output_reasoning"]["template"],
        },
        {"role": "user", "content": f"Research task: {task}"},
        {
            "role": "user",
            "content": "Dialog history (for reasoning context):\n" + dialog_snapshot,
        },
        {
            "role": "user",
            "content": (
                f"Current state:\n"
                f"- searches_total: {context.get('searches_total', 0)}\n"
                f"- clarification_used: {context.get('clarification_used', False)}\n"
                f"- report_created: {context.get('report_created', False)}\n"
                f"- known_sources: {len(context.get('sources', {}))}\n"
                f"- last_queries: {[s.get('query') for s in context.get('searches', [])[-3:]]}\n"
                "Return ReasoningStep object - analyze situation and decide next action."
            ),
        },
    ]

    completion = client.chat.completions.create(
        model=CONFIG["openai_model"],
        temperature=CONFIG["so_temperature"],
        max_tokens=CONFIG["max_tokens"],
        messages=so_messages,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "ReasoningStep",
                "schema": schema,
            },
        },
    )

    content = completion.choices[0].message.content or "{}"
    try:
        rs = ReasoningStep.model_validate_json(content)
    except ValidationError as ve:
        print(
            Panel(
                str(ve),
                title="❌ SO: Валидация ReasoningStep не прошла",
                border_style="red",
            )
        )
        return {"error": "validation_error", "details": json.loads(ve.json())}

    errors = validate_reasoning_step(rs, context)
    if errors:
        return {"error": "reasoning_validation_failed", "errors": errors}

    return {"reasoning": json.loads(rs.model_dump_json())}


def exec_action_phase(
    messages: List[Dict[str, Any]], reasoning: ReasoningStep, context: Dict[str, Any]
) -> None:
    """Phase 2: Let model execute appropriate tools based on reasoning"""
    print(f"[cyan]Phase 2: Executing action '{reasoning.next_action}'...[/cyan]")

    # Model decides what tools to call
    completion = client.chat.completions.create(
        model=CONFIG["openai_model"],
        temperature=CONFIG["temperature"],
        max_tokens=CONFIG["max_tokens"],
        tools=get_all_tools(),
        tool_choice="auto",  # Let model decide!
        messages=messages,
    )
    msg = completion.choices[0].message

    # Process tool calls or text response
    if getattr(msg, "tool_calls", None):
        # Model called tools
        tc_dump = [
            {
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in msg.tool_calls
        ]

        messages.append(
            {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": tc_dump,
            }
        )

        # Execute each tool call
        for tc in msg.tool_calls:
            result = execute_tool_call(tc, context)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
    else:
        # Model didn't call tools - just text response
        messages.append(
            {
                "role": "assistant",
                "content": msg.content or "No action taken",
            }
        )


def execute_tool_call(tool_call, context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a single tool call"""
    tool_name = tool_call.function.name

    try:
        tool_args = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError:
        tool_args = {}

    # Execute tool locally
    if tool_name in executors:
        # Convert args to appropriate model and execute
        if tool_name == "clarification":
            step = ClarificationStep(tool="clarification", **tool_args)
            return executors[tool_name](step, context)
        elif tool_name == "web_search":
            step = WebSearchStep(tool="web_search", **tool_args)
            return executors[tool_name](step, context, tavily)
        elif tool_name == "create_report":
            step = CreateReportStep(tool="create_report", **tool_args)
            return executors[tool_name](step, context, CONFIG)
        elif tool_name == "report_completion":
            step = ReportCompletionStep(tool="report_completion", **tool_args)
            return executors[tool_name](step, context)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    else:
        return {"error": f"No executor for tool: {tool_name}"}


# =============================================================================
# MAIN RESEARCH ORCHESTRATION
# =============================================================================


async def run_research(task: str) -> None:
    """Main research orchestration - two-phase approach"""
    print(Panel(task, title="🔍 Research Task", title_align="left"))
    print(
        f"[green]🚀 Launch[/green]  model={CONFIG['openai_model']}  base_url={openai_kwargs.get('base_url','default')}"
    )

    # Initialize conversation
    messages: List[Dict[str, Any]] = [
        {
            "role": "system",
            "content": PROMPTS["outer_system"]["template"].format(user_request=task),
        },
        {"role": "user", "content": task},
    ]
    context = create_fresh_context()

    # Main research loop
    rounds = 0
    while rounds < CONFIG["max_rounds"]:
        rounds += 1
        print(Rule(f"[bold]Round {rounds} — Reasoning + Action[/bold]"))

        try:
            # Phase 1: Reasoning Analysis
            reasoning = exec_reasoning_phase(messages, task, context)

            # Check completion
            if reasoning.task_completed:
                print(
                    Panel(
                        "Task marked as completed by reasoning.",
                        title="🏁 Completion",
                        border_style="green",
                    )
                )
                break

            # Phase 2: Execute Actions
            exec_action_phase(messages, reasoning, context)

        except Exception as e:
            print(
                Panel(
                    f"Error in round {rounds}: {e}",
                    title="❌ Error",
                    border_style="red",
                )
            )
            continue

    # Final statistics
    print(Rule("[dim]Session statistics[/dim]"))
    print(
        f"🔎 Searches: {context['searches_total']} | Sources: {len(context['sources'])}"
    )
    print(f"📁 Reports: ./{CONFIG['reports_directory']}/")


# =============================================================================
# CLI
# =============================================================================


def main():
    """Main CLI entry point"""
    print("[bold]🧠 SGR Research Agent — Two-Phase Architecture[/bold]\n")

    try:
        while True:
            task = input("🔍 Enter research task (or 'quit'): ").strip()
            if task.lower() in ("quit", "exit"):
                print("👋 Exit.")
                break
            if not task:
                print("⚠️ Empty input, try again.")
                continue

            asyncio.run(run_research(task))

    except KeyboardInterrupt:
        print("\n👋 Interrupted by user.")


if __name__ == "__main__":
    main()
