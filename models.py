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
    """Ask clarifying questions when facing ambiguous requests"""

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
    """Search for information with credibility focus"""

    tool: Literal["web_search"]
    reasoning: str = Field(description="Why this search is needed and what to expect")
    query: str = Field(description="Search query in same language as user request")
    max_results: int = Field(default=10, description="Maximum results (1-15)")
    plan_adapted: bool = Field(
        default=False, description="Is this search after plan adaptation?"
    )


class CreateReportStep(BaseModel):
    """Create comprehensive research report with citations"""

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
    """Complete research task"""

    tool: Literal["report_completion"]
    reasoning: str = Field(description="Why research is now complete")
    completed_steps: Annotated[List[str], MinLen(1), MaxLen(5)] = Field(
        description="Summary of completed steps"
    )
    status: Literal["completed", "failed"] = Field(description="Task completion status")


# Union type for all function steps
FunctionStep = Annotated[
    Union[
        ClarificationStep,
        WebSearchStep,
        CreateReportStep,
        ReportCompletionStep,
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
    next_action: Literal["search", "clarify", "report", "complete"] = Field(
        description="What should be done next"
    )
    action_reasoning: str = Field(description="Why this specific action is needed now")

    # Task completion
    task_completed: bool = Field(description="Is the research task finished?")

    # Remaining work
    remaining_steps: Annotated[
        List[str],
        Field(
            min_length=0,
            max_length=3,
            description="0-3 remaining steps (empty when task completed)",
        ),
    ]
