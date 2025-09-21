"""JobError Pydantic model for job failure information.

This module defines the JobError model used for capturing and storing
error information when research jobs fail.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
from enum import Enum


class ErrorType(str, Enum):
    """Job error type classifications."""
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    VALIDATION_ERROR = "validation_error"
    API_ERROR = "api_error"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION_ERROR = "authentication_error"
    PERMISSION_ERROR = "permission_error"
    RESOURCE_ERROR = "resource_error"
    AGENT_ERROR = "agent_error"
    SYSTEM_ERROR = "system_error"
    USER_CANCELLED = "user_cancelled"
    UNKNOWN_ERROR = "unknown_error"


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"           # Minor issues, warnings
    MEDIUM = "medium"     # Significant but recoverable errors
    HIGH = "high"         # Major errors affecting job completion
    CRITICAL = "critical" # Fatal errors requiring intervention


class JobError(BaseModel):
    """Error model for failed research jobs.

    This model captures comprehensive error information when jobs fail,
    providing details for debugging and potential recovery.
    """

    job_id: str = Field(
        ...,
        regex=r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        description="Reference to the failed job"
    )

    error_type: ErrorType = Field(
        ...,
        description="Error classification for categorization"
    )

    error_message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Human-readable error description"
    )

    error_code: Optional[str] = Field(
        default=None,
        description="Specific error code for programmatic handling"
    )

    error_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Technical error information and context"
    )

    severity: ErrorSeverity = Field(
        default=ErrorSeverity.HIGH,
        description="Error severity level"
    )

    retry_count: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Number of retry attempts made"
    )

    is_retryable: bool = Field(
        default=False,
        description="Whether job can be automatically retried"
    )

    occurred_at: datetime = Field(
        ...,
        description="Error occurrence timestamp"
    )

    # Contextual information
    agent_step: Optional[str] = Field(
        default=None,
        description="Research step where error occurred"
    )

    progress_at_failure: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Job progress percentage when error occurred"
    )

    stack_trace: Optional[str] = Field(
        default=None,
        description="Technical stack trace for debugging"
    )

    # Recovery information
    suggested_actions: List[str] = Field(
        default_factory=list,
        description="Suggested actions for error resolution"
    )

    recovery_hints: Dict[str, Any] = Field(
        default_factory=dict,
        description="Technical hints for automated recovery"
    )

    # External system information
    upstream_service: Optional[str] = Field(
        default=None,
        description="External service that caused the error"
    )

    upstream_error_code: Optional[str] = Field(
        default=None,
        description="Error code from upstream service"
    )

    # Monitoring and alerting
    alert_sent: bool = Field(
        default=False,
        description="Whether monitoring alert was sent"
    )

    requires_intervention: bool = Field(
        default=False,
        description="Whether manual intervention is required"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error record creation timestamp"
    )

    @validator('error_message')
    def validate_error_message(cls, v):
        """Validate and clean error message."""
        if not v or not v.strip():
            raise ValueError("error_message cannot be empty")

        # Clean and normalize the message
        cleaned = ' '.join(v.split())

        # Remove sensitive information patterns
        import re
        # Remove potential API keys, tokens, passwords
        cleaned = re.sub(r'\b[A-Za-z0-9]{32,}\b', '[REDACTED]', cleaned)
        cleaned = re.sub(r'password[=:]\s*\S+', 'password=[REDACTED]', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'token[=:]\s*\S+', 'token=[REDACTED]', cleaned, flags=re.IGNORECASE)

        return cleaned

    @validator('error_details')
    def validate_error_details(cls, v):
        """Validate and sanitize error details."""
        if not v:
            return {}

        # Remove sensitive information from error details
        sanitized = {}
        sensitive_keys = {'password', 'token', 'key', 'secret', 'credential'}

        for key, value in v.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = '[REDACTED]'
            else:
                sanitized[key] = value

        return sanitized

    @validator('suggested_actions')
    def validate_suggested_actions(cls, v):
        """Validate suggested actions list."""
        if not v:
            return []

        # Clean and limit actions
        cleaned_actions = []
        for action in v:
            if isinstance(action, str) and action.strip():
                cleaned_action = action.strip()[:200]  # Limit length
                cleaned_actions.append(cleaned_action)

        return cleaned_actions[:10]  # Limit to 10 actions

    @validator('stack_trace')
    def validate_stack_trace(cls, v):
        """Validate and limit stack trace size."""
        if not v:
            return None

        # Limit stack trace size to prevent excessive storage
        max_length = 10000  # 10KB limit
        if len(v) > max_length:
            return v[:max_length] + "\n... [TRUNCATED]"

        return v

    def is_transient_error(self) -> bool:
        """Check if error is likely transient and worth retrying."""
        transient_types = {
            ErrorType.NETWORK_ERROR,
            ErrorType.TIMEOUT,
            ErrorType.RATE_LIMIT,
            ErrorType.RESOURCE_ERROR
        }
        return self.error_type in transient_types and self.retry_count < 3

    def should_retry_automatically(self) -> bool:
        """Determine if job should be automatically retried."""
        if not self.is_retryable:
            return False

        if self.retry_count >= 3:
            return False

        if self.severity == ErrorSeverity.CRITICAL:
            return False

        return self.is_transient_error()

    def get_retry_delay_seconds(self) -> int:
        """Calculate retry delay using exponential backoff."""
        if not self.should_retry_automatically():
            return 0

        # Exponential backoff: 2^retry_count * base_delay
        base_delay = 60  # 1 minute base delay
        max_delay = 3600  # 1 hour maximum

        delay = min(base_delay * (2 ** self.retry_count), max_delay)
        return delay

    def add_suggested_action(self, action: str) -> None:
        """Add a suggested action for error resolution."""
        if action and action.strip():
            if action not in self.suggested_actions:
                self.suggested_actions.append(action.strip()[:200])

    def add_recovery_hint(self, key: str, value: Any) -> None:
        """Add a recovery hint for automated systems."""
        if key and key.strip():
            self.recovery_hints[key] = value

    def to_user_friendly_message(self) -> str:
        """Generate user-friendly error message."""
        error_messages = {
            ErrorType.NETWORK_ERROR: "Unable to connect to research services. Please check your internet connection.",
            ErrorType.TIMEOUT: "The research operation took too long to complete. Try reducing the scope or increasing the timeout.",
            ErrorType.VALIDATION_ERROR: "The research request contains invalid parameters. Please check your input.",
            ErrorType.API_ERROR: "External research services are currently unavailable. Please try again later.",
            ErrorType.RATE_LIMIT: "Too many requests have been made. Please wait before submitting new research jobs.",
            ErrorType.AUTHENTICATION_ERROR: "Authentication failed. Please check your API credentials.",
            ErrorType.PERMISSION_ERROR: "Insufficient permissions to perform this research operation.",
            ErrorType.RESOURCE_ERROR: "Insufficient system resources to complete the research. Try again later.",
            ErrorType.AGENT_ERROR: "The research agent encountered an internal error. Please contact support.",
            ErrorType.SYSTEM_ERROR: "A system error occurred. Please contact support if the problem persists.",
            ErrorType.USER_CANCELLED: "The research job was cancelled by the user.",
            ErrorType.UNKNOWN_ERROR: "An unexpected error occurred. Please contact support."
        }

        base_message = error_messages.get(self.error_type, self.error_message)

        if self.is_retryable and self.retry_count < 3:
            base_message += " This job can be retried automatically."

        return base_message

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "error_type": "network_error",
                "error_message": "Failed to connect to research API after 3 attempts",
                "error_code": "CONN_TIMEOUT",
                "error_details": {
                    "service": "tavily_api",
                    "endpoint": "https://api.tavily.com/search",
                    "timeout_seconds": 30,
                    "attempts": 3
                },
                "severity": "high",
                "retry_count": 2,
                "is_retryable": True,
                "occurred_at": "2024-01-21T10:35:00Z",
                "agent_step": "Searching for relevant sources",
                "progress_at_failure": 25.0,
                "suggested_actions": [
                    "Check network connectivity",
                    "Verify API credentials",
                    "Try again in a few minutes"
                ],
                "upstream_service": "tavily_api",
                "requires_intervention": False
            }
        }