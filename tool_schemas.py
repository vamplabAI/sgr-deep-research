#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SGR Research Agent - OpenAI Tool Schemas
Содержит схемы всех OpenAI function calls
"""

from typing import Any, Dict


# =============================================================================
# ALLOWED TOOLS
# =============================================================================

ALLOWED_TOOL_NAMES = [
    "clarification",
    "generate_reasoning",
    "web_search",
    "create_report",
    "report_completion",
    "read_local_file",
    "create_local_file",
    "update_local_file",
    "list_directory",
    "create_directory",
    "simple_answer",
    "get_current_datetime",
]


# =============================================================================
# TOOL SCHEMA FUNCTIONS
# =============================================================================


def tool_schema_generate_reasoning() -> Dict[str, Any]:
    """Schema for reasoning analysis tool."""
    return {
        "type": "function",
        "function": {
            "name": "generate_reasoning",
            "description": "Generate reasoning about current situation and next action. Takes no arguments.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    }


def tool_schema_clarification() -> Dict[str, Any]:
    """Schema for clarification tool."""
    return {
        "type": "function",
        "function": {
            "name": "clarification",
            "description": "Ask clarifying questions when request is ambiguous",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "Justification for needing clarification",
                    },
                    "unclear_terms": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 5,
                        "items": {"type": "string"},
                        "description": "List of unclear terms or concepts",
                    },
                    "assumptions": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 4,
                        "items": {"type": "string"},
                        "description": "Possible interpretations to verify",
                    },
                    "questions": {
                        "type": "array",
                        "minItems": 3,
                        "maxItems": 5,
                        "items": {"type": "string"},
                        "description": "3-5 specific clarifying questions",
                    },
                },
                "required": ["reasoning", "unclear_terms", "assumptions", "questions"],
                "additionalProperties": False,
            },
        },
    }


def tool_schema_web_search() -> Dict[str, Any]:
    """Schema for web search tool."""
    return {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search for information with credibility focus",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "Why this search is needed and what to expect",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query in same language as user request",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 15,
                        "default": 10,
                        "description": "Maximum number of results (1-15)",
                    },
                    "plan_adapted": {
                        "type": "boolean",
                        "default": False,
                        "description": "Is this search after plan adaptation?",
                    },
                },
                "required": ["reasoning", "query"],
                "additionalProperties": False,
            },
        },
    }


def tool_schema_create_report() -> Dict[str, Any]:
    """Schema for report creation tool."""
    return {
        "type": "function",
        "function": {
            "name": "create_report",
            "description": "Create comprehensive research report with citations",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "Why ready to create report now",
                    },
                    "title": {
                        "type": "string",
                        "description": "Report title",
                    },
                    "user_request_language_reference": {
                        "type": "string",
                        "description": "Copy of original user request to ensure language consistency",
                    },
                    "content": {
                        "type": "string",
                        "description": "COMPREHENSIVE RESEARCH REPORT (1500-2000+ words) with extensive analysis and citations",
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Confidence in findings",
                    },
                },
                "required": [
                    "reasoning",
                    "title",
                    "user_request_language_reference",
                    "content",
                    "confidence",
                ],
                "additionalProperties": False,
            },
        },
    }


def tool_schema_report_completion() -> Dict[str, Any]:
    """Schema for task completion tool."""
    return {
        "type": "function",
        "function": {
            "name": "report_completion",
            "description": "Complete research task",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "Why research is now complete",
                    },
                    "completed_steps": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 5,
                        "items": {"type": "string"},
                        "description": "Summary of completed steps",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["completed", "failed"],
                        "description": "Task completion status",
                    },
                },
                "required": ["reasoning", "completed_steps", "status"],
                "additionalProperties": False,
            },
        },
    }


def tool_schema_read_local_file() -> Dict[str, Any]:
    """Schema for reading local files."""
    return {
        "type": "function",
        "function": {
            "name": "read_local_file",
            "description": "Read content from a local file for analysis or research",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "Why this file needs to be read and how it relates to research",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read (relative or absolute)",
                    },
                    "encoding": {
                        "type": "string",
                        "default": "utf-8",
                        "description": "File encoding (default: utf-8)",
                    },
                },
                "required": ["reasoning", "file_path"],
                "additionalProperties": False,
            },
        },
    }


def tool_schema_create_local_file() -> Dict[str, Any]:
    """Schema for creating local files."""
    return {
        "type": "function",
        "function": {
            "name": "create_local_file",
            "description": "Create a new local file with specified content",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "Why this file needs to be created and its purpose",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path where the file should be created (relative or absolute)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file",
                    },
                    "encoding": {
                        "type": "string",
                        "default": "utf-8",
                        "description": "File encoding (default: utf-8)",
                    },
                    "overwrite": {
                        "type": "boolean",
                        "default": False,
                        "description": "Whether to overwrite if file exists (default: false)",
                    },
                },
                "required": ["reasoning", "file_path", "content"],
                "additionalProperties": False,
            },
        },
    }


def tool_schema_update_local_file() -> Dict[str, Any]:
    """Schema for updating existing local files."""
    return {
        "type": "function",
        "function": {
            "name": "update_local_file",
            "description": "Update content in an existing local file",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "Why this file needs to be updated and what changes are needed",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to update",
                    },
                    "operation": {
                        "type": "string",
                        "enum": [
                            "append",
                            "prepend",
                            "replace_content",
                            "replace_section",
                        ],
                        "description": "Type of update operation",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to add or replacement content",
                    },
                    "search_text": {
                        "type": "string",
                        "description": "Text to search for (required for replace_section operation)",
                    },
                    "encoding": {
                        "type": "string",
                        "default": "utf-8",
                        "description": "File encoding (default: utf-8)",
                    },
                },
                "required": ["reasoning", "file_path", "operation", "content"],
                "additionalProperties": False,
            },
        },
    }


def tool_schema_list_directory() -> Dict[str, Any]:
    """Schema for listing directory contents."""
    return {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List contents of a directory (files and subdirectories)",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "Why this directory listing is needed for the research",
                    },
                    "directory_path": {
                        "type": "string",
                        "description": "Path to the directory to list (default: current directory '.')",
                        "default": ".",
                    },
                    "show_hidden": {
                        "type": "boolean",
                        "default": False,
                        "description": "Whether to show hidden files and directories (starting with .)",
                    },
                    "recursive": {
                        "type": "boolean",
                        "default": False,
                        "description": "Whether to list subdirectories recursively",
                    },
                    "max_depth": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                        "default": 1,
                        "description": "Maximum depth for recursive listing (1-5)",
                    },
                    "tree_view": {
                        "type": "boolean",
                        "default": False,
                        "description": "Display results in tree format with visual hierarchy",
                    },
                },
                "required": ["reasoning"],
                "additionalProperties": False,
            },
        },
    }


def tool_schema_create_directory() -> Dict[str, Any]:
    """Schema for creating directories with user confirmation."""
    return {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "Create a new directory with user confirmation",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "Why this directory needs to be created and its purpose",
                    },
                    "directory_path": {
                        "type": "string",
                        "description": "Path where the directory should be created",
                    },
                    "create_parents": {
                        "type": "boolean",
                        "default": True,
                        "description": "Whether to create parent directories if they don't exist",
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of what this directory will contain",
                    },
                },
                "required": ["reasoning", "directory_path", "description"],
                "additionalProperties": False,
            },
        },
    }


def tool_schema_simple_answer() -> Dict[str, Any]:
    """Schema for providing simple direct answers."""
    return {
        "type": "function",
        "function": {
            "name": "simple_answer",
            "description": "Provide a direct, concise answer to user's question without creating a formal report",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "Why a simple answer is appropriate for this request",
                    },
                    "answer": {
                        "type": "string",
                        "description": "Direct, concise answer to the user's question",
                    },
                    "additional_info": {
                        "type": "string",
                        "description": "Optional additional context or helpful information",
                        "default": "",
                    },
                },
                "required": ["reasoning", "answer"],
                "additionalProperties": False,
            },
        },
    }


def tool_schema_get_current_datetime() -> Dict[str, Any]:
    """Schema for getting current date and time."""
    return {
        "type": "function",
        "function": {
            "name": "get_current_datetime",
            "description": "Get current date and time in various formats",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "Why current date/time is needed for the task",
                    },
                    "format": {
                        "type": "string",
                        "enum": [
                            "date_only",
                            "time_only",
                            "datetime",
                            "iso",
                            "human_readable",
                        ],
                        "default": "human_readable",
                        "description": "Format for the date/time output",
                    },
                    "timezone": {
                        "type": "string",
                        "default": "Europe/Moscow",
                        "description": "Timezone for the result (default: Europe/Moscow)",
                    },
                },
                "required": ["reasoning"],
                "additionalProperties": False,
            },
        },
    }


# =============================================================================
# ALL TOOLS COLLECTION
# =============================================================================


def get_all_tools() -> list[Dict[str, Any]]:
    """Get all tool schemas."""
    return [
        tool_schema_clarification(),
        tool_schema_generate_reasoning(),
        tool_schema_web_search(),
        tool_schema_create_report(),
        tool_schema_report_completion(),
        tool_schema_read_local_file(),
        tool_schema_create_local_file(),
        tool_schema_update_local_file(),
        tool_schema_list_directory(),
        tool_schema_create_directory(),
        tool_schema_simple_answer(),
        tool_schema_get_current_datetime(),
    ]


# =============================================================================
# TOOL CHOICE HELPERS
# =============================================================================


def make_tool_choice_generate_reasoning() -> Dict[str, Any]:
    """Force model to call generate_reasoning tool."""
    return {"type": "function", "function": {"name": "generate_reasoning"}}
