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
]


# =============================================================================
# TOOL SCHEMA FUNCTIONS
# =============================================================================


def tool_schema_generate_reasoning() -> Dict[str, Any]:
    """Schema for reasoning analysis tool"""
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
    """Schema for clarification tool"""
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
    """Schema for web search tool"""
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
    """Schema for report creation tool"""
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
    """Schema for task completion tool"""
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


# =============================================================================
# ALL TOOLS COLLECTION
# =============================================================================


def get_all_tools() -> list[Dict[str, Any]]:
    """Get all tool schemas"""
    return [
        tool_schema_clarification(),
        tool_schema_generate_reasoning(),
        tool_schema_web_search(),
        tool_schema_create_report(),
        tool_schema_report_completion(),
    ]


# =============================================================================
# TOOL CHOICE HELPERS
# =============================================================================


def make_tool_choice_generate_reasoning() -> Dict[str, Any]:
    """Force model to call generate_reasoning tool"""
    return {"type": "function", "function": {"name": "generate_reasoning"}}
