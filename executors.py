#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SGR Research Agent - Function Executors
Содержит исполнителей всех функций агента
"""

import os
import json
from datetime import datetime
from typing import Any, Dict

from rich.console import Console
from rich.panel import Panel

from models import (
    ClarificationStep,
    WebSearchStep,
    CreateReportStep,
    ReportCompletionStep,
)

# Инициализация консоли
console = Console()
print = console.print


# =============================================================================
# CONTEXT & SOURCES
# =============================================================================


def add_citation(context: Dict[str, Any], url: str, title: str = "") -> int:
    """Add citation and return citation number"""
    if url in context["sources"]:
        return context["sources"][url]["number"]
    context["citation_counter"] += 1
    num = context["citation_counter"]
    context["sources"][url] = {"number": num, "title": title or "", "url": url}
    return num


def format_sources_block(context: Dict[str, Any]) -> str:
    """Format sources for report footer"""
    if not context["sources"]:
        return ""
    lines = ["", "## Sources"]
    for url, data in context["sources"].items():
        t = data["title"]
        n = data["number"]
        if t:
            lines.append(f"- [{n}] {t} - {url}")
        else:
            lines.append(f"- [{n}] {url}")
    return "\n".join(lines)


# =============================================================================
# FUNCTION EXECUTORS
# =============================================================================


def exec_clarification(
    step: ClarificationStep, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute clarification step - ask user for clarification"""
    context["clarification_used"] = True
    print("\n[bold yellow]🤔 CLARIFYING INFORMATION NEEDED[/bold yellow]")
    print(f"💭 Reason: {step.reasoning}")

    if step.unclear_terms:
        print("❓ Unclear terms: " + ", ".join(step.unclear_terms))

    if step.questions:
        print("\n[cyan]Questions for clarification:[/cyan]")
        for i, q in enumerate(step.questions, 1):
            print(f"   {i}. {q}")

    if step.assumptions:
        print("\n[green]Possible interpretations:[/green]")
        for a in step.assumptions:
            print(f"   • {a}")

    # Wait for user response
    print("\n[bold cyan]Please clarify your request:[/bold cyan]")
    try:
        user_clarification = input(">>> ").strip()
        if not user_clarification or user_clarification.lower() in ["quit", "exit"]:
            return {
                "tool": "clarification",
                "status": "cancelled",
                "user_input": "User cancelled",
            }

        return {
            "tool": "clarification",
            "status": "completed",
            "user_input": user_clarification,
            "questions": step.questions,
        }
    except (KeyboardInterrupt, EOFError):
        return {
            "tool": "clarification",
            "status": "cancelled",
            "user_input": "User cancelled",
        }


def exec_web_search(
    step: WebSearchStep, context: Dict[str, Any], tavily_client
) -> Dict[str, Any]:
    """Execute web search step"""
    q = step.query
    mx = int(step.max_results or 10)
    print(f"\n[cyan]🔎 Search:[/cyan] '{q}' (max={mx})")

    try:
        resp = tavily_client.search(query=q, max_results=mx)
        cits = []
        for r in resp.get("results", []):
            url = r.get("url", "")
            title = r.get("title", "")
            if url:
                cits.append(add_citation(context, url, title))

        context["searches"].append(
            {
                "query": q,
                "timestamp": datetime.now().isoformat(),
                "results": resp.get("results", []),
                "citation_numbers": cits,
            }
        )
        context["searches_total"] += 1

        if cits:
            for i, (r, c) in enumerate(zip(resp.get("results", [])[:5], cits[:5]), 1):
                print(f"   {i}. [{c}] {r.get('title','Untitled')} — {r.get('url','')}")

        return {
            "query": q,
            "results_count": len(resp.get("results", [])),
            "citations": cits,
        }
    except Exception as e:
        print(f"[red]Search error:[/red] {e}")
        return {"error": str(e), "query": q}


def exec_create_report(
    step: CreateReportStep, context: Dict[str, Any], config: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute report creation step"""
    # Set flag that report is created
    context["report_created"] = True

    os.makedirs(config["reports_directory"], exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c for c in step.title if c.isalnum() or c in (" ", "-", "_"))[
        :60
    ]
    filename = f"{ts}_{safe_title}.md"
    path = os.path.join(config["reports_directory"], filename)

    content = f"# {step.title}\n\n*Created: {datetime.now():%Y-%m-%d %H:%M:%S}*\n\n"
    content += step.content
    content += format_sources_block(context)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    words = len(step.content.split())
    print("\n[bold blue]📄 Report created[/bold blue]")
    print(f"💾 File: {path}")
    print(
        f"📊 Words: {words} | Sources: {len(context['sources'])} | Confidence: {step.confidence}"
    )

    return {
        "title": step.title,
        "filepath": path,
        "word_count": words,
        "confidence": step.confidence,
    }


def exec_report_completion(
    step: ReportCompletionStep, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute task completion step"""
    print("\n[bold green]✅ Research completed[/bold green]")
    for s in step.completed_steps:
        print(f"   • {s}")
    return {"status": step.status}


# =============================================================================
# EXECUTOR REGISTRY
# =============================================================================


def get_executors() -> Dict[str, callable]:
    """Get all function executors"""
    return {
        "clarification": exec_clarification,
        "web_search": exec_web_search,
        "create_report": exec_create_report,
        "report_completion": exec_report_completion,
    }
