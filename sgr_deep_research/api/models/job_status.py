"""JobStatus Pydantic model for job state tracking.

This module defines the JobStatus model used for tracking the current state
and progress of running jobs in the SGR Deep Research system.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator
from enum import Enum


class JobState(str, Enum):
    """Job execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStatus(BaseModel):
    """Status model for tracking job progress and state.

    This model tracks the current state and progress of a running job,
    providing real-time information about execution progress.
    """

    job_id: str = Field(
        ...,
        pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        description="Unique job identifier (UUID4 format)"
    )

    status: JobState = Field(
        ...,
        description="Current job execution state"
    )

    progress: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Completion percentage (0.0-100.0)"
    )

    current_step: str = Field(
        default="",
        max_length=500,
        description="Description of current operation being performed"
    )

    steps_completed: int = Field(
        default=0,
        ge=0,
        description="Number of research steps completed"
    )

    total_steps: int = Field(
        default=0,
        ge=0,
        description="Total estimated steps for this job"
    )

    searches_used: int = Field(
        default=0,
        ge=0,
        description="Number of search operations performed"
    )

    sources_found: int = Field(
        default=0,
        ge=0,
        description="Number of research sources discovered"
    )

    created_at: datetime = Field(
        ...,
        description="Job submission timestamp"
    )

    started_at: Optional[datetime] = Field(
        default=None,
        description="Job execution start time"
    )

    completed_at: Optional[datetime] = Field(
        default=None,
        description="Job completion/failure time"
    )

    estimated_completion: Optional[datetime] = Field(
        default=None,
        description="Projected completion time"
    )

    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last status update timestamp"
    )

    # Optional fields for detailed tracking
    query: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Truncated version of original query for display"
    )

    agent_type: Optional[str] = Field(
        default=None,
        description="Agent type being used for execution"
    )

    tags: Optional[list[str]] = Field(
        default=None,
        description="Job tags for filtering and organization"
    )

    priority: Optional[int] = Field(
        default=None,
        description="Job priority level"
    )

    runtime_seconds: Optional[float] = Field(
        default=None,
        ge=0,
        description="Total runtime in seconds (for completed jobs)"
    )

    @model_validator(mode='after')
    def validate_model(self):
        """Validate model fields consistency."""
        # Validate progress is consistent with status
        if self.status == JobState.PENDING and self.progress != 0.0:
            raise ValueError("Pending jobs must have 0% progress")

        if self.status == JobState.COMPLETED and self.progress != 100.0:
            raise ValueError("Completed jobs must have 100% progress")

        if self.status == JobState.RUNNING and (self.progress <= 0.0 or self.progress >= 100.0):
            raise ValueError("Running jobs must have progress between 0% and 100%")

        # Validate steps_completed doesn't exceed total_steps
        if self.total_steps > 0 and self.steps_completed > self.total_steps:
            raise ValueError("steps_completed cannot exceed total_steps")

        # Validate completed_at is consistent with status
        terminal_states = {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED}

        if self.status in terminal_states and self.completed_at is None:
            raise ValueError(f"Jobs in {self.status} state must have completed_at timestamp")

        if self.status not in terminal_states and self.completed_at is not None:
            raise ValueError(f"Jobs in {self.status} state cannot have completed_at timestamp")

        # Validate started_at is consistent with status
        if self.status in {JobState.RUNNING, JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED} and self.started_at is None:
            # Only pending jobs should not have started_at
            if self.status != JobState.PENDING:
                raise ValueError(f"Jobs in {self.status} state must have started_at timestamp")

        # Validate estimated_completion is in the future for running jobs
        if self.estimated_completion is not None and self.created_at is not None:
            if self.estimated_completion <= self.created_at:
                raise ValueError("estimated_completion must be after created_at")

        # Only running jobs should have estimated completion
        if self.estimated_completion is not None and self.status not in {JobState.PENDING, JobState.RUNNING}:
            raise ValueError("Only pending/running jobs can have estimated_completion")

        return self

    def calculate_progress_from_steps(self) -> float:
        """Calculate progress percentage from completed steps."""
        if self.total_steps <= 0:
            return 0.0

        progress = (self.steps_completed / self.total_steps) * 100.0
        return min(100.0, max(0.0, progress))

    def update_runtime(self) -> None:
        """Update runtime_seconds based on current timestamps."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.runtime_seconds = delta.total_seconds()
        elif self.started_at:
            # For running jobs, calculate current runtime
            delta = datetime.utcnow() - self.started_at
            self.runtime_seconds = delta.total_seconds()

    def is_terminal_state(self) -> bool:
        """Check if job is in a terminal (finished) state."""
        return self.status in {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED}

    def can_be_cancelled(self) -> bool:
        """Check if job can be cancelled."""
        return self.status in {JobState.PENDING, JobState.RUNNING}

    def get_display_query(self, max_length: int = 100) -> str:
        """Get truncated query for display purposes."""
        if not self.query:
            return ""

        if len(self.query) <= max_length:
            return self.query

        return self.query[:max_length - 3] + "..."

    model_config = {
        "use_enum_values": True,
        "validate_assignment": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat() if v else None
        },
        "json_schema_extra": {
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "running",
                "progress": 45.0,
                "current_step": "Analyzing search results from 5 sources",
                "steps_completed": 9,
                "total_steps": 20,
                "searches_used": 3,
                "sources_found": 12,
                "created_at": "2024-01-21T10:30:00Z",
                "started_at": "2024-01-21T10:30:05Z",
                "estimated_completion": "2024-01-21T10:45:00Z",
                "last_updated": "2024-01-21T10:35:30Z",
                "query": "What are the latest developments in AI research?",
                "agent_type": "sgr-tools",
                "tags": ["ai", "research"],
                "priority": 0
            }
        }
    }