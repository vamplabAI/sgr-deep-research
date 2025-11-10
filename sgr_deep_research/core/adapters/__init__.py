"""Адаптеры для работы с различными моделями."""

from sgr_deep_research.core.adapters.qwen3_thinking_adapter import (
    extract_structured_response,
    robust_json_extract,
    extract_tool_call_from_tags,
)

__all__ = [
    "extract_structured_response",
    "robust_json_extract",
    "extract_tool_call_from_tags",
]
