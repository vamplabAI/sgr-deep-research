"""API models package for SGR Deep Research job management.

This package contains all Pydantic models used for job submission,
status tracking, results, and error handling.
"""

from .job_request import JobRequest, AgentType
from .job_status import JobStatus, JobState
from .job_result import JobResult, FileArtifact
from .job_error import JobError, ErrorType, ErrorSeverity
from .research_source import ResearchSource, SourceType, SourceStatus
from .execution_metrics import ExecutionMetrics, CostBreakdown, PerformanceMetrics

# Legacy API models for compatibility - defined inline to avoid circular imports
from enum import Enum
from typing import Any, Dict, List, Literal
from pydantic import BaseModel, Field

class AgentModel(str, Enum):
    """Available agent models for chat completion."""
    SGR_TOOLS_AGENT = "sgr-tools-agent"

# Mapping will be populated later to avoid circular import
AGENT_MODEL_MAPPING = {}

class ChatMessage(BaseModel):
    """Chat message."""
    role: Literal["system", "user", "assistant", "tool"] = Field(default="user", description="Sender role")
    content: str = Field(description="Message content")

class ChatCompletionRequest(BaseModel):
    """Request for creating chat completion."""
    model: str | None = Field(
        default=AgentModel.SGR_TOOLS_AGENT,
        description="Agent type or existing agent identifier",
        example="sgr-tools-agent",
    )
    messages: List[ChatMessage] = Field(description="List of messages")
    stream: bool = Field(default=True, description="Enable streaming mode")
    max_tokens: int | None = Field(default=1500, description="Maximum number of tokens")
    temperature: float | None = Field(default=0, description="Generation temperature")

class ChatCompletionChoice(BaseModel):
    """Choice in chat completion response."""
    index: int = Field(description="Choice index")
    message: ChatMessage = Field(description="Response message")
    finish_reason: str | None = Field(description="Finish reason")

class ChatCompletionResponse(BaseModel):
    """Chat completion response (non-streaming)."""
    id: str = Field(description="Response ID")
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(description="Creation time")
    model: str = Field(description="Model used")
    choices: List[ChatCompletionChoice] = Field(description="List of choices")
    usage: Dict[str, int] | None = Field(default=None, description="Usage information")

class HealthResponse(BaseModel):
    status: Literal["healthy"] = "healthy"
    service: str = Field(default="SGR Deep Research API", description="Service name")

class AgentStateResponse(BaseModel):
    agent_id: str = Field(description="Agent ID")
    task: str = Field(description="Agent task")
    state: str = Field(description="Current agent state")
    searches_used: int = Field(description="Number of searches performed")
    clarifications_used: int = Field(description="Number of clarifications requested")
    sources_count: int = Field(description="Number of sources found")
    current_state: Dict[str, Any] | None = Field(default=None, description="Current agent step")

class AgentListItem(BaseModel):
    agent_id: str = Field(description="Agent ID")
    task: str = Field(description="Agent task")
    state: str = Field(description="Current agent state")

class AgentListResponse(BaseModel):
    agents: List[AgentListItem] = Field(description="List of agents")
    total: int = Field(description="Total number of agents")

__all__ = [
    # Core job models
    "JobRequest",
    "JobStatus",
    "JobResult",
    "JobError",

    # Supporting models
    "ResearchSource",
    "ExecutionMetrics",
    "FileArtifact",
    "CostBreakdown",
    "PerformanceMetrics",

    # Enums
    "AgentType",
    "JobState",
    "ErrorType",
    "ErrorSeverity",
    "SourceType",
    "SourceStatus",

    # Legacy API models
    "AGENT_MODEL_MAPPING",
    "AgentModel",
    "ChatMessage",
    "ChatCompletionRequest",
    "ChatCompletionChoice",
    "ChatCompletionResponse",
    "HealthResponse",
    "AgentStateResponse",
    "AgentListItem",
    "AgentListResponse",
]