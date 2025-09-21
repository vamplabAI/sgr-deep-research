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
]