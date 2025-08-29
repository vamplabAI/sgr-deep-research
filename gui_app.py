#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SGR Research Agent - Chainlit GUI Interface
Beautiful web interface for the research agent with tool support
Updated with all new tools: file operations, directory management, simple answers, etc.
"""

import json
import os
import asyncio
from typing import Any, Dict, List
from datetime import datetime

import chainlit as cl
from openai import AsyncOpenAI
from tavily import TavilyClient
from dotenv import load_dotenv

# Load environment variables (optional, config.yaml takes priority)
load_dotenv()

# Local modules
from models import (  # noqa: E402
    ReasoningStep,
    ClarificationStep,
    WebSearchStep,
    CreateReportStep,
    ReportCompletionStep,
    ReadLocalFileStep,
    CreateLocalFileStep,
    UpdateLocalFileStep,
    ListDirectoryStep,
    CreateDirectoryStep,
    SimpleAnswerStep,
    GetCurrentDatetimeStep,
)
from tool_schemas import (  # noqa: E402
    get_all_tools,
    make_tool_choice_generate_reasoning,
)
from sgr_agent import (  # noqa: E402
    load_config,
    load_prompts,
    create_fresh_context,
    validate_reasoning_step,
)

# =============================================================================
# CONFIGURATION
# =============================================================================

CONFIG = load_config()
PROMPTS = load_prompts()

# Initialize clients
openai_kwargs = {"api_key": CONFIG["openai_api_key"]}
if CONFIG["openai_base_url"]:
    openai_kwargs["base_url"] = CONFIG["openai_base_url"]

client = AsyncOpenAI(**openai_kwargs)
tavily = TavilyClient(CONFIG["tavily_api_key"])

# =============================================================================
# CHAINLIT HELPER FUNCTIONS
# =============================================================================


async def display_reasoning_step(rs: ReasoningStep) -> None:
    """Display reasoning step beautifully."""

    # Main information as a table
    reasoning_table = f"""
**🎯 Current Situation:** {rs.current_situation}

**📋 Plan Status:** {rs.plan_status}

**🧠 Reasoning Steps:**
{chr(10).join([f"• {step}" for step in rs.reasoning_steps])}

**🎬 Next Action:** `{rs.next_action}`

**💭 Action Reasoning:** {rs.action_reasoning}

**📊 Statistics:**
- Searches done: {rs.searches_done}
- Enough data: {"✅" if rs.enough_data else "❌"}
- Task completed: {"✅" if rs.task_completed else "❌"}

**📝 Next Steps:**
{chr(10).join([f"→ {step}" for step in rs.next_steps]) if rs.next_steps else "No next steps"}
    """

    msg = cl.Message(
        author="🧠 Analysis",
        content=reasoning_table,
    )
    await msg.send()


async def display_search_results(
    search_data: Dict[str, Any], context: Dict[str, Any]
) -> None:
    """Display search results beautifully."""

    query = search_data.get("query", "")
    results_count = search_data.get("results_count", 0)
    citations = search_data.get("citations", [])

    # Get detailed results from context
    last_search = context.get("searches", [])[-1] if context.get("searches") else {}
    results = last_search.get("results", [])

    search_summary = f"""
🔍 **Query:** `{query}`
📊 **Found:** {results_count} results
📚 **Citations:** {', '.join([f'[{c}]' for c in citations[:5]])}
    """

    # Elements with search results
    elements = []
    for i, result in enumerate(results[:5], 1):
        title = result.get("title", "Untitled")
        url = result.get("url", "")
        content = (
            result.get("content", "")[:200] + "..." if result.get("content") else ""
        )

        citation_num = citations[i - 1] if i - 1 < len(citations) else i

        elements.append(
            cl.Text(
                name=f"result_{i}",
                content=f"**[{citation_num}] {title}**\n\n{content}\n\n🔗 {url}",
                display="inline",
            )
        )

    msg = cl.Message(author="🔍 Search", content=search_summary, elements=elements)
    await msg.send()


async def display_report_created(report_data: Dict[str, Any]) -> None:
    """Display information about created report beautifully."""

    title = report_data.get("title", "Report")
    filepath = report_data.get("filepath", "")
    word_count = report_data.get("word_count", 0)
    confidence = report_data.get("confidence", "unknown")

    confidence_emoji = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(confidence, "⚪")

    report_info = f"""
📄 **Report created successfully!**

**📝 Title:** {title}
**💾 File:** `{filepath}`
**📊 Words:** {word_count}
**🎯 Confidence:** {confidence_emoji} {confidence.upper()}

Report saved and ready for viewing!
    """

    # Read report content for display
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        elements = [cl.Text(name="report_content", content=content, display="inline")]
    except Exception:
        elements = []

    msg = cl.Message(author="📄 Report", content=report_info, elements=elements)
    await msg.send()


async def display_file_operation(
    operation_type: str, operation_data: Dict[str, Any]
) -> None:
    """Display file operation result beautifully."""

    if operation_type == "read_file":
        filepath = operation_data.get("filepath", "")
        size = operation_data.get("size", 0)
        content = operation_data.get("content", "")

        info = f"""
📖 **File Read Successfully**

**📁 File:** `{filepath}`
**📏 Size:** {size} bytes

**Content Preview:**
```
{content[:500]}{'...' if len(content) > 500 else ''}
```
        """

        elements = [cl.Text(name="file_content", content=content, display="inline")]

    elif operation_type == "create_file":
        filepath = operation_data.get("filepath", "")
        size = operation_data.get("size", 0)

        info = f"""
📝 **File Created Successfully**

**📁 File:** `{filepath}`
**📏 Size:** {size} bytes

File has been created and is ready for use.
        """
        elements = []

    elif operation_type == "update_file":
        filepath = operation_data.get("filepath", "")
        operation = operation_data.get("operation", "")

        info = f"""
✏️ **File Updated Successfully**

**📁 File:** `{filepath}`
**🔄 Operation:** {operation}

File has been updated with new content.
        """
        elements = []

    elif operation_type == "list_directory":
        directory = operation_data.get("directory", "")
        items = operation_data.get("items", [])
        tree_view = operation_data.get("tree_view", False)

        info = f"""
📂 **Directory Listed**

**📁 Directory:** `{directory}`
**📊 Items:** {len(items)} items

{'Tree view:' if tree_view else 'Contents:'}
```
{chr(10).join(items[:20])}
{'...' if len(items) > 20 else ''}
```
        """
        elements = []

    elif operation_type == "create_directory":
        directory = operation_data.get("directory", "")

        info = f"""
📁 **Directory Created**

**📂 Directory:** `{directory}`

Directory has been created successfully.
        """
        elements = []
    else:
        info = f"**Operation completed:** {operation_type}"
        elements = []

    msg = cl.Message(author="📁 File Operation", content=info, elements=elements)
    await msg.send()


# =============================================================================
# TOOL EXECUTION FUNCTIONS
# =============================================================================


@cl.step(type="tool", name="clarification")
async def exec_clarification_gui(
    step: ClarificationStep, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute clarification in GUI format."""
    context["clarification_used"] = True

    questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(step.questions)])
    assumptions_text = "\n".join([f"• {a}" for a in step.assumptions])
    unclear_terms_text = ", ".join(step.unclear_terms)

    clarification_content = f"""
🤔 **Need Clarification**

**💭 Reason:** {step.reasoning}

**❓ Unclear Terms:** {unclear_terms_text}

**🎯 Possible Interpretations:**
{assumptions_text}

**❓ Clarifying Questions:**
{questions_text}

**Please provide clarification in your next message. The research will pause until you respond.**
    """

    msg = cl.Message(
        author="🤔 Clarification",
        content=clarification_content,
    )
    await msg.send()

    # Set flag to wait for user input
    context["waiting_for_clarification"] = True
    context["clarification_questions"] = step.questions

    return {
        "tool": "clarification",
        "status": "waiting_for_user_input",
        "questions": step.questions,
        "reasoning": step.reasoning,
        "message": "Waiting for user clarification",
    }


@cl.step(type="tool", name="web_search")
async def exec_web_search_gui(
    step: WebSearchStep, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute web search in GUI format."""

    query = step.query
    max_results = step.max_results or 10

    try:
        # Execute search
        resp = await asyncio.to_thread(
            tavily.search, query=query, max_results=max_results
        )

        # Process results
        citations = []
        for r in resp.get("results", []):
            url = r.get("url", "")
            title = r.get("title", "")
            if url:
                citation_num = add_citation(context, url, title)
                citations.append(citation_num)

        # Save to context
        context["searches"].append(
            {
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "results": resp.get("results", []),
                "citation_numbers": citations,
            }
        )
        context["searches_total"] += 1

        search_data = {
            "query": query,
            "results_count": len(resp.get("results", [])),
            "citations": citations,
        }

        # Display results
        await display_search_results(search_data, context)

        return search_data

    except Exception as e:
        error_msg = cl.Message(
            author="❌ Search Error",
            content=f"Error during search: {str(e)}\nQuery: {query}",
        )
        await error_msg.send()

        return {"error": str(e), "query": query}


@cl.step(type="tool", name="create_report")
async def exec_create_report_gui(
    step: CreateReportStep, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Create report in GUI format."""

    # Set flag
    context["report_created"] = True

    # Create directory if needed
    os.makedirs(CONFIG["reports_directory"], exist_ok=True)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c for c in step.title if c.isalnum() or c in (" ", "-", "_"))[
        :60
    ]
    filename = f"{timestamp}_{safe_title}.md"
    filepath = os.path.join(CONFIG["reports_directory"], filename)

    # Format content
    content = f"# {step.title}\n\n*Created: {datetime.now():%Y-%m-%d %H:%M:%S}*\n\n"
    content += step.content
    content += format_sources_block(context)

    # Save file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    word_count = len(step.content.split())

    report_data = {
        "title": step.title,
        "filepath": filepath,
        "word_count": word_count,
        "confidence": step.confidence,
    }

    # Display report information
    await display_report_created(report_data)

    return report_data


@cl.step(type="tool", name="simple_answer")
async def exec_simple_answer_gui(
    step: SimpleAnswerStep, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute simple answer in GUI format."""

    answer_content = f"""
💬 **Quick Answer**

**💭 Reasoning:** {step.reasoning}

**📝 Answer:**
{step.answer}
    """

    msg = cl.Message(
        author="💬 Quick Answer",
        content=answer_content,
    )
    await msg.send()

    return {
        "tool": "simple_answer",
        "status": "completed",
        "answer": step.answer,
        "reasoning": step.reasoning,
    }


@cl.step(type="tool", name="get_current_datetime")
async def exec_get_datetime_gui(
    step: GetCurrentDatetimeStep, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute get current datetime in GUI format."""

    current_time = datetime.now()

    datetime_info = f"""
🕐 **Current Date & Time**

**💭 Reasoning:** {step.reasoning}

**📅 Current Date:** {current_time.strftime("%Y-%m-%d")}
**🕐 Current Time:** {current_time.strftime("%H:%M:%S")}
**🌍 Timezone:** {step.timezone}
**📆 Day of Week:** {current_time.strftime("%A")}
    """

    msg = cl.Message(
        author="🕐 DateTime",
        content=datetime_info,
    )
    await msg.send()

    return {
        "tool": "get_current_datetime",
        "status": "completed",
        "current_datetime": current_time.isoformat(),
        "timezone": step.timezone,
    }


@cl.step(type="tool", name="read_local_file")
async def exec_read_file_gui(
    step: ReadLocalFileStep, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute read local file in GUI format."""

    try:
        with open(step.file_path, "r", encoding=step.encoding) as f:
            content = f.read()

        file_size = os.path.getsize(step.file_path)

        operation_data = {
            "filepath": step.file_path,
            "content": content,
            "size": file_size,
        }

        await display_file_operation("read_file", operation_data)

        return {
            "tool": "read_local_file",
            "status": "completed",
            "filepath": step.file_path,
            "content": content,
            "size": file_size,
        }

    except Exception as e:
        error_msg = cl.Message(
            author="❌ File Error",
            content=f"Error reading file: {str(e)}\nFile: {step.file_path}",
        )
        await error_msg.send()

        return {"error": str(e), "filepath": step.file_path}


@cl.step(type="tool", name="create_local_file")
async def exec_create_file_gui(
    step: CreateLocalFileStep, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute create local file in GUI format."""

    try:
        # Check if file exists and overwrite flag
        if os.path.exists(step.file_path) and not step.overwrite:
            error_msg = cl.Message(
                author="❌ File Error",
                content=f"File already exists: {step.file_path}\nUse overwrite=true to replace it.",
            )
            await error_msg.send()
            return {"error": "file_exists", "filepath": step.file_path}

        # Create directories if needed
        os.makedirs(os.path.dirname(step.file_path) or ".", exist_ok=True)

        # Write file
        with open(step.file_path, "w", encoding=step.encoding) as f:
            f.write(step.content)

        file_size = os.path.getsize(step.file_path)

        operation_data = {
            "filepath": step.file_path,
            "size": file_size,
        }

        await display_file_operation("create_file", operation_data)

        return {
            "tool": "create_local_file",
            "status": "completed",
            "filepath": step.file_path,
            "size": file_size,
        }

    except Exception as e:
        error_msg = cl.Message(
            author="❌ File Error",
            content=f"Error creating file: {str(e)}\nFile: {step.file_path}",
        )
        await error_msg.send()

        return {"error": str(e), "filepath": step.file_path}


@cl.step(type="tool", name="update_local_file")
async def exec_update_file_gui(
    step: UpdateLocalFileStep, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute update local file in GUI format."""

    try:
        # Read existing content
        with open(step.file_path, "r", encoding=step.encoding) as f:
            original_content = f.read()

        # Perform operation
        if step.operation == "append":
            new_content = original_content + step.content
        elif step.operation == "prepend":
            new_content = step.content + original_content
        elif step.operation == "replace_content":
            new_content = step.content
        elif step.operation == "replace_section":
            if step.search_text in original_content:
                new_content = original_content.replace(step.search_text, step.content)
            else:
                error_msg = cl.Message(
                    author="❌ File Error",
                    content=f"Search text not found in file: {step.search_text}",
                )
                await error_msg.send()
                return {"error": "search_text_not_found", "filepath": step.file_path}
        else:
            return {"error": "invalid_operation", "operation": step.operation}

        # Write updated content
        with open(step.file_path, "w", encoding=step.encoding) as f:
            f.write(new_content)

        operation_data = {
            "filepath": step.file_path,
            "operation": step.operation,
        }

        await display_file_operation("update_file", operation_data)

        return {
            "tool": "update_local_file",
            "status": "completed",
            "filepath": step.file_path,
            "operation": step.operation,
        }

    except Exception as e:
        error_msg = cl.Message(
            author="❌ File Error",
            content=f"Error updating file: {str(e)}\nFile: {step.file_path}",
        )
        await error_msg.send()

        return {"error": str(e), "filepath": step.file_path}


@cl.step(type="tool", name="list_directory")
async def exec_list_directory_gui(
    step: ListDirectoryStep, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute list directory in GUI format."""

    try:
        items = []

        if step.tree_view:
            # Generate tree view
            def build_tree(path, prefix="", max_depth=step.max_depth, current_depth=0):
                if current_depth >= max_depth:
                    return []

                tree_items = []
                try:
                    entries = sorted(os.listdir(path))
                    if not step.show_hidden:
                        entries = [e for e in entries if not e.startswith(".")]

                    for i, entry in enumerate(entries):
                        entry_path = os.path.join(path, entry)
                        is_last = i == len(entries) - 1

                        if os.path.isdir(entry_path):
                            connector = "└── " if is_last else "├── "
                            tree_items.append(f"{prefix}{connector}📁 {entry}/")

                            if step.recursive and current_depth < max_depth - 1:
                                extension = "    " if is_last else "│   "
                                tree_items.extend(
                                    build_tree(
                                        entry_path,
                                        prefix + extension,
                                        max_depth,
                                        current_depth + 1,
                                    )
                                )
                        else:
                            connector = "└── " if is_last else "├── "
                            tree_items.append(f"{prefix}{connector}📄 {entry}")

                except PermissionError:
                    tree_items.append(f"{prefix}❌ Permission denied")

                return tree_items

            items = build_tree(step.directory_path)
        else:
            # Regular listing
            try:
                entries = os.listdir(step.directory_path)
                if not step.show_hidden:
                    entries = [e for e in entries if not e.startswith(".")]

                for entry in sorted(entries):
                    entry_path = os.path.join(step.directory_path, entry)
                    if os.path.isdir(entry_path):
                        items.append(f"📁 {entry}/")
                    else:
                        items.append(f"📄 {entry}")

            except PermissionError:
                items = ["❌ Permission denied"]

        operation_data = {
            "directory": step.directory_path,
            "items": items,
            "tree_view": step.tree_view,
        }

        await display_file_operation("list_directory", operation_data)

        return {
            "tool": "list_directory",
            "status": "completed",
            "directory": step.directory_path,
            "items": items,
            "count": len(items),
        }

    except Exception as e:
        error_msg = cl.Message(
            author="❌ Directory Error",
            content=f"Error listing directory: {str(e)}\nDirectory: {step.directory_path}",
        )
        await error_msg.send()

        return {"error": str(e), "directory": step.directory_path}


@cl.step(type="tool", name="create_directory")
async def exec_create_directory_gui(
    step: CreateDirectoryStep, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute create directory in GUI format."""

    try:
        # Create directory
        os.makedirs(step.directory_path, exist_ok=True)

        operation_data = {
            "directory": step.directory_path,
        }

        await display_file_operation("create_directory", operation_data)

        return {
            "tool": "create_directory",
            "status": "completed",
            "directory": step.directory_path,
        }

    except Exception as e:
        error_msg = cl.Message(
            author="❌ Directory Error",
            content=f"Error creating directory: {str(e)}\nDirectory: {step.directory_path}",
        )
        await error_msg.send()

        return {"error": str(e), "directory": step.directory_path}


@cl.step(type="tool", name="report_completion")
async def exec_report_completion_gui(
    step: ReportCompletionStep, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Complete task in GUI format."""

    completed_steps_text = "\n".join([f"✅ {s}" for s in step.completed_steps])

    completion_content = f"""
🎉 **Research completed!**

**💭 Reasoning:** {step.reasoning}

**📋 Completed steps:**
{completed_steps_text}

**📊 Status:** {step.status.upper()}
    """

    msg = cl.Message(
        author="🏁 Completion",
        content=completion_content,
    )
    await msg.send()

    return {"status": step.status}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def add_citation(context: Dict[str, Any], url: str, title: str = "") -> int:
    """Add citation and return number."""
    if url in context["sources"]:
        return context["sources"][url]["number"]
    context["citation_counter"] += 1
    num = context["citation_counter"]
    context["sources"][url] = {"number": num, "title": title or "", "url": url}
    return num


def format_sources_block(context: Dict[str, Any]) -> str:
    """Format sources block for report."""
    if not context["sources"]:
        return ""
    lines = ["", "## Sources"]
    for url, data in context["sources"].items():
        title = data["title"]
        num = data["number"]
        if title:
            lines.append(f"- [{num}] {title} - {url}")
        else:
            lines.append(f"- [{num}] {url}")
    return "\n".join(lines)


# =============================================================================
# MAIN EXECUTION FUNCTIONS
# =============================================================================


async def exec_reasoning_phase_gui(
    messages: List[Dict[str, Any]], task: str, context: Dict[str, Any]
) -> ReasoningStep:
    """Phase 1: Situation analysis for GUI"""

    # Force reasoning call
    completion = await client.chat.completions.create(
        model=CONFIG["openai_model"],
        temperature=CONFIG["temperature"],
        max_tokens=CONFIG["max_tokens"],
        tools=get_all_tools(),
        tool_choice=make_tool_choice_generate_reasoning(),
        messages=messages,
    )
    msg = completion.choices[0].message

    # Validation
    if (
        not getattr(msg, "tool_calls", None)
        or len(msg.tool_calls) != 1
        or msg.tool_calls[0].function.name != "generate_reasoning"
    ):
        raise RuntimeError("Expected one 'generate_reasoning' call")

    # Add to message log
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

    # Execute structured output reasoning
    reasoning_result = await exec_structured_output_reasoning_gui(
        messages, task, context
    )

    # Add result to log
    messages.append(
        {
            "role": "tool",
            "tool_call_id": reasoning_call_id,
            "content": json.dumps(reasoning_result, ensure_ascii=False),
        }
    )

    if "error" in reasoning_result:
        raise RuntimeError(f"Reasoning validation error: {reasoning_result['error']}")

    reasoning = ReasoningStep.model_validate(reasoning_result["reasoning"])

    # Display reasoning
    await display_reasoning_step(reasoning)

    return reasoning


async def exec_structured_output_reasoning_gui(
    messages: List[Dict[str, Any]], task: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Internal Structured Output call for reasoning."""

    schema = ReasoningStep.model_json_schema()

    # Build dialog snapshot
    dialog_snapshot = "\n".join(
        [
            f"{m.get('role', '').upper()}: {str(m.get('content', ''))[:500]}..."
            for m in messages[-10:]  # Last 10 messages
        ]
    )

    so_messages = [
        {
            "role": "system",
            "content": PROMPTS["structured_output_reasoning"]["template"],
        },
        {"role": "user", "content": f"Research task: {task}"},
        {
            "role": "user",
            "content": f"Dialog history:\n{dialog_snapshot}",
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

    completion = await client.chat.completions.create(
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
    except Exception as e:
        return {"error": "validation_error", "details": str(e)}

    # Validation against context
    errors = validate_reasoning_step(rs, context)
    if errors:
        return {"error": "reasoning_validation_failed", "errors": errors}

    return {"reasoning": json.loads(rs.model_dump_json())}


async def exec_action_phase_gui(
    messages: List[Dict[str, Any]], reasoning: ReasoningStep, context: Dict[str, Any]
) -> None:
    """Phase 2: Action execution in GUI"""

    # Model decides which tools to call
    completion = await client.chat.completions.create(
        model=CONFIG["openai_model"],
        temperature=CONFIG["temperature"],
        max_tokens=CONFIG["max_tokens"],
        tools=get_all_tools(),
        tool_choice="auto",
        messages=messages,
    )
    msg = completion.choices[0].message

    # Process tool calls or text response
    if getattr(msg, "tool_calls", None):
        # Model called tools
        tc_dump = []
        for tc in msg.tool_calls:
            tc_dump.append(
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
            )

        messages.append(
            {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": tc_dump,
            }
        )

        # Execute each tool call
        for tc in msg.tool_calls:
            # Save tool call ID for clarification
            if tc.function.name == "clarification":
                context["last_clarification_call_id"] = tc.id

            result = await execute_tool_call_gui(tc, context)

            # Always add tool response (OpenAI requires response to every tool_call)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
    else:
        # Model didn't call tools - just text response
        if msg.content:
            text_msg = cl.Message(author="🤖 Agent", content=msg.content)
            await text_msg.send()

        messages.append(
            {
                "role": "assistant",
                "content": msg.content or "No action taken",
            }
        )


async def execute_tool_call_gui(tool_call, context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute tool call in GUI."""

    tool_name = tool_call.function.name

    try:
        tool_args = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError:
        tool_args = {}

    # Execute tool
    if tool_name == "clarification":
        step = ClarificationStep(tool="clarification", **tool_args)
        return await exec_clarification_gui(step, context)
    elif tool_name == "web_search":
        step = WebSearchStep(tool="web_search", **tool_args)
        return await exec_web_search_gui(step, context)
    elif tool_name == "create_report":
        step = CreateReportStep(tool="create_report", **tool_args)
        return await exec_create_report_gui(step, context)
    elif tool_name == "simple_answer":
        step = SimpleAnswerStep(tool="simple_answer", **tool_args)
        return await exec_simple_answer_gui(step, context)
    elif tool_name == "get_current_datetime":
        step = GetCurrentDatetimeStep(tool="get_current_datetime", **tool_args)
        return await exec_get_datetime_gui(step, context)
    elif tool_name == "read_local_file":
        step = ReadLocalFileStep(tool="read_local_file", **tool_args)
        return await exec_read_file_gui(step, context)
    elif tool_name == "create_local_file":
        step = CreateLocalFileStep(tool="create_local_file", **tool_args)
        return await exec_create_file_gui(step, context)
    elif tool_name == "update_local_file":
        step = UpdateLocalFileStep(tool="update_local_file", **tool_args)
        return await exec_update_file_gui(step, context)
    elif tool_name == "list_directory":
        step = ListDirectoryStep(tool="list_directory", **tool_args)
        return await exec_list_directory_gui(step, context)
    elif tool_name == "create_directory":
        step = CreateDirectoryStep(tool="create_directory", **tool_args)
        return await exec_create_directory_gui(step, context)
    elif tool_name == "report_completion":
        step = ReportCompletionStep(tool="report_completion", **tool_args)
        return await exec_report_completion_gui(step, context)
    else:
        return {"error": f"Unknown tool: {tool_name}"}


async def continue_research_after_clarification(
    context: Dict[str, Any], message_history: List[Dict[str, Any]], original_task: str
) -> None:
    """Continue research after receiving user clarification."""

    # Continue the research loop from where it was paused
    rounds = context.get("current_round", 0)
    max_rounds = CONFIG["max_rounds"]

    while rounds < max_rounds:
        rounds += 1
        context["current_round"] = rounds

        # Show progress
        progress_msg = cl.Message(
            author="🔄 Process",
            content=f"**Round {rounds}/{max_rounds}** - Continuing analysis after clarification...",
        )
        await progress_msg.send()

        try:
            # Phase 1: Situation analysis
            reasoning = await exec_reasoning_phase_gui(
                message_history, original_task, context
            )

            # Check completion
            if reasoning.task_completed:
                completion_msg = cl.Message(
                    author="🏁 Completion",
                    content="**Task marked as completed by analysis.**",
                )
                await completion_msg.send()
                break

            # Phase 2: Action execution
            await exec_action_phase_gui(message_history, reasoning, context)

            # If clarification was requested again, break and wait
            if context.get("waiting_for_clarification", False):
                break

        except Exception as e:
            error_msg = cl.Message(
                author="❌ Error", content=f"Error in round {rounds}: {str(e)}"
            )
            await error_msg.send()
            continue

    # Save updated context
    cl.user_session.set("context", context)
    cl.user_session.set("message_history", message_history)


# =============================================================================
# CHAINLIT EVENT HANDLERS
# =============================================================================


@cl.on_chat_start
async def start_chat():
    """Chat initialization."""

    # Create fresh context
    context = create_fresh_context()

    # Save to session
    cl.user_session.set("context", context)
    cl.user_session.set("message_history", [])

    # Welcome message
    welcome_msg = f"""
# 🧠 SGR Research Agent - Web Interface

Welcome to the intelligent research system!

**🔍 Agent Capabilities:**
- **Situation Analysis** - smart research planning
- **Web Search** - finding credible information via Tavily
- **Clarification** - questions for better task understanding
- **Report Creation** - detailed research reports with citations
- **File Operations** - read, create, and update local files
- **Directory Management** - browse and organize file structures
- **Quick Answers** - fast responses without full reports
- **Date/Time Awareness** - current date and time information

**🚀 Configuration:**
- Model: `{CONFIG["openai_model"]}`
- Max Searches: {CONFIG["max_searches_total"]}
- Max Rounds: {CONFIG["max_rounds"]}

**Simply ask your research question or request any file operation, and I'll conduct deep analysis!**
    """

    await cl.Message(author="🤖 System", content=welcome_msg).send()


@cl.on_message
async def handle_message(message: cl.Message):
    """Handle user message."""

    # Get context and history
    context = cl.user_session.get("context", create_fresh_context())
    message_history = cl.user_session.get("message_history", [])

    user_content = message.content.strip()

    if not user_content:
        await cl.Message(
            author="⚠️ System",
            content="Please enter your research request.",
        ).send()
        return

    # Check if we're waiting for clarification
    if context.get("waiting_for_clarification", False):
        # Process user clarification
        context["waiting_for_clarification"] = False
        clarification_questions = context.get("clarification_questions", [])

        # Add clarification to message history
        message_history.append(
            {"role": "user", "content": f"Clarification: {user_content}"}
        )

        # Update the last tool response with actual user clarification
        last_call_id = context.get("last_clarification_call_id", "clarification_1")

        # Find and update the tool response for clarification
        for i in range(len(message_history) - 1, -1, -1):
            msg = message_history[i]
            if msg.get("role") == "tool" and msg.get("tool_call_id") == last_call_id:
                msg["content"] = json.dumps(
                    {
                        "tool": "clarification",
                        "status": "completed",
                        "user_input": user_content,
                        "questions": clarification_questions,
                    },
                    ensure_ascii=False,
                )
                break

        # Show acknowledgment
        await cl.Message(
            author="✅ Clarification Received",
            content=f"**Your clarification:** {user_content}\n\n**Continuing research with this information...**",
        ).send()

        # Continue research loop from where it was paused
        original_task = context.get("original_task", user_content)
        await continue_research_after_clarification(
            context, message_history, original_task
        )
        return

    # Check commands
    if user_content.lower() in ["help", "помощь"]:
        help_msg = """
**🆘 Command Help:**

- Simply ask a research question or request file operations
- Agent will automatically conduct analysis
- Supported commands: `help`, `stats`, `clear`

**Example queries:**
- "Research the electric vehicle market in 2024"
- "Analyze latest achievements in AI"
- "Read the contents of report.txt"
- "Create a summary file of our discussion"
- "List files in the current directory"
        """
        await cl.Message(author="🆘 Help", content=help_msg).send()
        return

    if user_content.lower() in ["stats", "статистика"]:
        stats_msg = f"""
**📊 Session Statistics:**

🔍 **Searches:** {context.get('searches_total', 0)} / {CONFIG['max_searches_total']}
📚 **Sources:** {len(context.get('sources', {}))}
❓ **Clarification used:** {'Yes' if context.get('clarification_used') else 'No'}
📄 **Report created:** {'Yes' if context.get('report_created') else 'No'}
💬 **Messages in history:** {len(message_history)}
        """
        await cl.Message(author="📊 Statistics", content=stats_msg).send()
        return

    if user_content.lower() in ["clear", "очистить"]:
        # Reset context
        context = create_fresh_context()
        message_history = []
        cl.user_session.set("context", context)
        cl.user_session.set("message_history", message_history)

        await cl.Message(
            author="🔄 System",
            content="Context cleared. You can start a new research!",
        ).send()
        return

    # Main research logic
    try:
        # Initialize message history if empty
        if not message_history:
            message_history = [
                {
                    "role": "system",
                    "content": PROMPTS["outer_system"]["template"].format(
                        user_request=user_content
                    ),
                }
            ]

        # Add user message
        message_history.append({"role": "user", "content": user_content})

        # Main research loop
        rounds = 0
        max_rounds = CONFIG["max_rounds"]

        while rounds < max_rounds:
            rounds += 1
            context["current_round"] = rounds

            # Show progress
            progress_msg = cl.Message(
                author="🔄 Process",
                content=f"**Round {rounds}/{max_rounds}** - Analysis and action execution...",
            )
            await progress_msg.send()

            try:
                # Phase 1: Situation analysis
                reasoning = await exec_reasoning_phase_gui(
                    message_history, user_content, context
                )

                # Check completion
                if reasoning.task_completed:
                    completion_msg = cl.Message(
                        author="🏁 Completion",
                        content="**Task marked as completed by analysis.**",
                    )
                    await completion_msg.send()
                    break

                # Phase 2: Action execution
                await exec_action_phase_gui(message_history, reasoning, context)

                # If clarification was requested, break and wait for user input
                if context.get("waiting_for_clarification", False):
                    context["original_task"] = user_content
                    await cl.Message(
                        author="⏸️ Research Paused",
                        content="**Research paused - waiting for your clarification.**",
                    ).send()
                    break

            except Exception as e:
                error_msg = cl.Message(
                    author="❌ Error", content=f"Error in round {rounds}: {str(e)}"
                )
                await error_msg.send()
                continue

        # Final statistics only if not waiting for clarification
        if not context.get("waiting_for_clarification", False):
            final_stats = f"""
**📊 Session completed:**

🔎 Searches: {context['searches_total']} | 📚 Sources: {len(context['sources'])}
📁 Reports saved to: `./{CONFIG['reports_directory']}/`
            """

            await cl.Message(author="📊 Summary", content=final_stats).send()

    except Exception as e:
        error_msg = cl.Message(
            author="❌ Critical Error",
            content=f"Critical error occurred: {str(e)}",
        )
        await error_msg.send()

    finally:
        # Save updated context
        cl.user_session.set("context", context)
        cl.user_session.set("message_history", message_history)


# =============================================================================
# CHAINLIT SETTINGS
# =============================================================================


@cl.set_chat_profiles
async def chat_profile():
    return [
        cl.ChatProfile(
            name="research",
            markdown_description="🧠 **Research Mode** - full analysis with search and reports",
        ),
    ]


if __name__ == "__main__":
    # Launch Chainlit application
    import chainlit as cl

    cl.run()
