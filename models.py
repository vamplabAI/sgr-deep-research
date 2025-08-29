#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SGR Research Agent - Pydantic Models
Содержит все модели данных для structured output и function calls
"""

from typing import List, Literal, Union
from annotated_types import MaxLen, MinLen
from typing_extensions import Annotated
from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# FUNCTION STEP MODELS
# =============================================================================


class ClarificationStep(BaseModel):
    """Ask clarifying questions when facing ambiguous requests."""

    tool: Literal["clarification"]
    reasoning: str = Field(description="Why clarification is needed")
    unclear_terms: Annotated[List[str], MinLen(1), MaxLen(5)] = Field(
        description="List of unclear terms or concepts"
    )
    assumptions: Annotated[List[str], MinLen(1), MaxLen(4)] = Field(
        description="Possible interpretations to verify (1-4 items)"
    )
    questions: Annotated[List[str], MinLen(3), MaxLen(5)] = Field(
        description="3-5 specific clarifying questions"
    )


class WebSearchStep(BaseModel):
    """Search for information with credibility focus."""

    tool: Literal["web_search"]
    reasoning: str = Field(description="Why this search is needed and what to expect")
    query: str = Field(description="Search query in same language as user request")
    max_results: int = Field(default=10, description="Maximum results (1-15)")
    plan_adapted: bool = Field(
        default=False, description="Is this search after plan adaptation?"
    )


class CreateReportStep(BaseModel):
    """Create comprehensive research report with citations."""

    tool: Literal["create_report"]
    reasoning: str = Field(description="Why ready to create report now")
    title: str = Field(description="Report title")
    user_request_language_reference: str = Field(
        description="Copy of original user request to ensure language consistency"
    )

    content: str = Field(
        description="""
    COMPREHENSIVE RESEARCH REPORT (1500-2000+ words) with extensive analysis and citations.

    THIS IS A RESEARCH OVERVIEW, NOT A BRIEF SUMMARY:
    - MINIMUM 1500-2000 words of detailed content
    - Each section should be 300-500 words with thorough analysis
    - Provide deep insights, comparisons, expert opinions
    - Include specific data, numbers, technical specifications
    - Reference multiple sources per topic
    - Analyze trends, market conditions, expert reviews
    - Compare different models, years, configurations when relevant

    LANGUAGE REQUIREMENTS:
    - WRITE ENTIRELY IN THE SAME LANGUAGE AS user_request_language_reference
    - Include in-text citations for EVERY fact using [1], [2], [3] etc.
    - Citations must be integrated into sentences, not separate

    MANDATORY STRUCTURE (each section 300-500 words):
    1. Executive Summary
       - Comprehensive overview of all findings
       - Key numbers, prices, technical specs

    2. Market Analysis
       - Current pricing trends and market position
       - Availability and demand analysis
       - Regional differences and market dynamics

    3. Technical Analysis
       - Detailed technical specifications
       - Engine performance and reliability data
       - Maintenance requirements and costs
       - Comparison with competitors

    4. Expert Opinions & User Reviews
       - Professional reviews and ratings
       - Owner experiences and feedback
       - Common issues and praise points

    5. Long-term Ownership Analysis
       - Reliability over time
       - Maintenance costs and schedules
       - Resale value and depreciation

    6. Key Findings
       - Summarize all major findings with data

    7. Conclusions & Recommendations
       - Final assessment and buying advice

    CONTENT DEPTH REQUIREMENTS:
    - Use data from AT LEAST 15-20 different sources
    - Include specific numbers (prices, specs, years, mileage)
    - Provide detailed explanations, not just facts
    - Analyze WHY certain trends exist
    - Compare multiple options/variants
    - Give context and background information
    """
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description="Confidence in findings"
    )


class ReportCompletionStep(BaseModel):
    """Complete research task."""

    tool: Literal["report_completion"]
    reasoning: str = Field(description="Why research is now complete")
    completed_steps: Annotated[List[str], MinLen(1), MaxLen(5)] = Field(
        description="Summary of completed steps"
    )
    status: Literal["completed", "failed"] = Field(description="Task completion status")


class ReadLocalFileStep(BaseModel):
    """Read content from a local file for analysis or research."""

    tool: Literal["read_local_file"]
    reasoning: str = Field(
        description="Why this file needs to be read and how it relates to research"
    )
    file_path: str = Field(
        description="Path to the file to read (relative or absolute)"
    )
    encoding: str = Field(default="utf-8", description="File encoding")


class CreateLocalFileStep(BaseModel):
    """Create a new local file with specified content."""

    tool: Literal["create_local_file"]
    reasoning: str = Field(
        description="Why this file needs to be created and its purpose"
    )
    file_path: str = Field(
        description="Path where the file should be created (relative or absolute)"
    )
    content: str = Field(description="Content to write to the file")
    encoding: str = Field(default="utf-8", description="File encoding")
    overwrite: bool = Field(
        default=False, description="Whether to overwrite if file exists"
    )


class UpdateLocalFileStep(BaseModel):
    """Update content in an existing local file."""

    tool: Literal["update_local_file"]
    reasoning: str = Field(
        description="Why this file needs to be updated and what changes are needed"
    )
    file_path: str = Field(description="Path to the file to update")
    operation: Literal["append", "prepend", "replace_content", "replace_section"] = (
        Field(description="Type of update operation")
    )
    content: str = Field(description="Content to add or replacement content")
    search_text: str = Field(
        default="",
        description="Text to search for (required for replace_section operation)",
    )
    encoding: str = Field(default="utf-8", description="File encoding")


class ListDirectoryStep(BaseModel):
    """List contents of a directory (files and subdirectories)"""

    tool: Literal["list_directory"]
    reasoning: str = Field(
        description="Why this directory listing is needed for the research"
    )
    directory_path: str = Field(
        default=".", description="Path to the directory to list"
    )
    show_hidden: bool = Field(
        default=False, description="Whether to show hidden files and directories"
    )
    recursive: bool = Field(
        default=False, description="Whether to list subdirectories recursively"
    )
    max_depth: int = Field(
        default=1, description="Maximum depth for recursive listing (1-5)"
    )
    tree_view: bool = Field(
        default=False,
        description="Display results in tree format with visual hierarchy",
    )


class CreateDirectoryStep(BaseModel):
    """Create a new directory with user confirmation."""

    tool: Literal["create_directory"]
    reasoning: str = Field(
        description="Why this directory needs to be created and its purpose"
    )
    directory_path: str = Field(
        description="Path where the directory should be created"
    )
    create_parents: bool = Field(
        default=True,
        description="Whether to create parent directories if they don't exist",
    )
    description: str = Field(
        description="Brief description of what this directory will contain"
    )


class SimpleAnswerStep(BaseModel):
    """Provide a direct, concise answer without creating a formal report."""

    tool: Literal["simple_answer"]
    reasoning: str = Field(
        description="Why a simple answer is appropriate for this request"
    )
    answer: str = Field(description="Direct, concise answer to the user's question")
    additional_info: str = Field(
        default="", description="Optional additional context or helpful information"
    )


class GetCurrentDatetimeStep(BaseModel):
    """Get current date and time in various formats."""

    tool: Literal["get_current_datetime"]
    reasoning: str = Field(description="Why current date/time is needed for the task")
    format: Literal["date_only", "time_only", "datetime", "iso", "human_readable"] = (
        Field(default="human_readable", description="Format for the date/time output")
    )
    timezone: str = Field(
        default="Europe/Moscow", description="Timezone for the result"
    )


# Union type for all function steps
FunctionStep = Annotated[
    Union[
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
    ],
    Field(discriminator="tool"),
]


# =============================================================================
# STRUCTURED OUTPUT MODELS
# =============================================================================


class ReasoningStep(BaseModel):
    """Pure reasoning without function calls - explains what and why"""

    model_config = ConfigDict(extra="forbid")

    # Reasoning chain
    reasoning_steps: Annotated[
        List[str],
        Field(
            min_length=1, max_length=4, description="Step-by-step reasoning, required"
        ),
    ]

    # Current state assessment
    current_situation: str = Field(description="Current research situation analysis")
    plan_status: str = Field(description="Status of current plan execution")

    # Progress tracking
    searches_done: int = Field(
        default=0, ge=0, description="Number of searches completed so far"
    )
    enough_data: bool = Field(default=False, description="Sufficient data for report?")

    # Next action decision
    next_action: Literal[
        "search",
        "clarify",
        "report",
        "complete",
        "read_file",
        "create_file",
        "update_file",
        "list_dir",
        "create_dir",
        "simple_answer",
        "get_datetime",
    ] = Field(description="What should be done next")
    action_reasoning: str = Field(description="Why this specific action is needed now")

    # Task completion
    task_completed: bool = Field(description="Is the research task finished?")

    # Planned next steps
    next_steps: Annotated[
        List[str],
        Field(
            min_length=0,
            max_length=3,
            description="0-3 next steps (empty when task completed)",
        ),
    ]
