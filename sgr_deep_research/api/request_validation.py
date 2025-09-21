"""Request validation middleware and utilities.

This module provides enhanced request validation, rate limiting,
and input sanitization for the SGR Deep Research API.
"""

import logging
import re
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from fastapi import Request, HTTPException
from pydantic import BaseModel, validator

from sgr_deep_research.api.models import JobRequest, AgentType

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom validation error."""

    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.message = message
        self.value = value
        super().__init__(f"Validation error for {field}: {message}")


class RateLimitTracker:
    """Simple in-memory rate limiting tracker."""

    def __init__(self, max_requests: int = 10, window_minutes: int = 5):
        self.max_requests = max_requests
        self.window = timedelta(minutes=window_minutes)
        self.requests: Dict[str, List[datetime]] = {}

    def is_rate_limited(self, client_id: str) -> bool:
        """Check if client is rate limited."""
        now = datetime.utcnow()
        cutoff = now - self.window

        # Get client's request history
        if client_id not in self.requests:
            self.requests[client_id] = []

        # Remove old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > cutoff
        ]

        # Check if limit exceeded
        if len(self.requests[client_id]) >= self.max_requests:
            return True

        # Add current request
        self.requests[client_id].append(now)
        return False

    def get_remaining_requests(self, client_id: str) -> int:
        """Get remaining requests for client."""
        if client_id not in self.requests:
            return self.max_requests

        now = datetime.utcnow()
        cutoff = now - self.window
        recent_requests = [
            req_time for req_time in self.requests[client_id]
            if req_time > cutoff
        ]

        return max(0, self.max_requests - len(recent_requests))


# Global rate limiter
rate_limiter = RateLimitTracker()


def get_client_id(request: Request) -> str:
    """Extract client identifier from request."""
    # Try to get real IP from headers (if behind proxy)
    real_ip = (
        request.headers.get("X-Real-IP") or
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or
        request.client.host if request.client else "unknown"
    )

    return real_ip


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware."""
    # Skip rate limiting for health checks
    if request.url.path in ["/health", "/docs", "/openapi.json"]:
        return await call_next(request)

    client_id = get_client_id(request)

    if rate_limiter.is_rate_limited(client_id):
        remaining = rate_limiter.get_remaining_requests(client_id)
        logger.warning(f"Rate limit exceeded for client {client_id}")

        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Too many requests.",
            headers={
                "X-RateLimit-Limit": str(rate_limiter.max_requests),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int((datetime.utcnow() + rate_limiter.window).timestamp()))
            }
        )

    response = await call_next(request)

    # Add rate limit headers to response
    remaining = rate_limiter.get_remaining_requests(client_id)
    response.headers["X-RateLimit-Limit"] = str(rate_limiter.max_requests)
    response.headers["X-RateLimit-Remaining"] = str(remaining)

    return response


class JobRequestValidator:
    """Enhanced validator for job requests."""

    # Patterns for validation
    SAFE_QUERY_PATTERN = re.compile(r"^[a-zA-Z0-9\s\.\,\?\!\-\_\(\)\[\]\:\"\'\/\+\=\&\%\$\@\#]+$")
    SUSPICIOUS_PATTERNS = [
        re.compile(r"<script", re.IGNORECASE),
        re.compile(r"javascript:", re.IGNORECASE),
        re.compile(r"data:text/html", re.IGNORECASE),
        re.compile(r"vbscript:", re.IGNORECASE),
        re.compile(r"onload\s*=", re.IGNORECASE),
        re.compile(r"onerror\s*=", re.IGNORECASE),
    ]

    @classmethod
    def validate_query(cls, query: str) -> str:
        """Validate and sanitize query string."""
        if not query or not query.strip():
            raise ValidationError("query", "Query cannot be empty")

        query = query.strip()

        if len(query) > 1000:
            raise ValidationError("query", "Query too long (max 1000 characters)", len(query))

        if len(query) < 3:
            raise ValidationError("query", "Query too short (min 3 characters)", len(query))

        # Check for suspicious patterns
        for pattern in cls.SUSPICIOUS_PATTERNS:
            if pattern.search(query):
                raise ValidationError("query", "Query contains potentially unsafe content")

        # Basic character validation (optional - might be too restrictive)
        # if not cls.SAFE_QUERY_PATTERN.match(query):
        #     raise ValidationError("query", "Query contains invalid characters")

        return query

    @classmethod
    def validate_agent_type(cls, agent_type: str) -> AgentType:
        """Validate agent type."""
        try:
            return AgentType(agent_type)
        except ValueError:
            valid_types = [t.value for t in AgentType]
            raise ValidationError(
                "agent_type",
                f"Invalid agent type. Must be one of: {', '.join(valid_types)}",
                agent_type
            )

    @classmethod
    def validate_deep_level(cls, deep_level: int) -> int:
        """Validate deep level parameter."""
        if deep_level < 0:
            raise ValidationError("deep_level", "Deep level cannot be negative", deep_level)

        if deep_level > 10:
            raise ValidationError("deep_level", "Deep level too high (max 10)", deep_level)

        return deep_level

    @classmethod
    def validate_priority(cls, priority: int) -> int:
        """Validate priority parameter."""
        if priority < -100:
            raise ValidationError("priority", "Priority too low (min -100)", priority)

        if priority > 100:
            raise ValidationError("priority", "Priority too high (max 100)", priority)

        return priority

    @classmethod
    def validate_tags(cls, tags: List[str]) -> List[str]:
        """Validate tags list."""
        if len(tags) > 10:
            raise ValidationError("tags", "Too many tags (max 10)", len(tags))

        validated_tags = []
        for tag in tags:
            if not isinstance(tag, str):
                raise ValidationError("tags", "All tags must be strings", type(tag))

            tag = tag.strip()
            if not tag:
                continue

            if len(tag) > 50:
                raise ValidationError("tags", "Tag too long (max 50 characters)", len(tag))

            if not re.match(r"^[a-zA-Z0-9\-\_]+$", tag):
                raise ValidationError("tags", "Tag contains invalid characters", tag)

            validated_tags.append(tag)

        return validated_tags

    @classmethod
    def validate_metadata(cls, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate metadata dictionary."""
        if len(metadata) > 20:
            raise ValidationError("metadata", "Too many metadata fields (max 20)", len(metadata))

        validated_metadata = {}
        for key, value in metadata.items():
            if not isinstance(key, str):
                raise ValidationError("metadata", "All metadata keys must be strings", type(key))

            if len(key) > 100:
                raise ValidationError("metadata", "Metadata key too long (max 100 characters)", len(key))

            if not re.match(r"^[a-zA-Z0-9\-\_\.]+$", key):
                raise ValidationError("metadata", "Metadata key contains invalid characters", key)

            # Convert value to string and limit length
            str_value = str(value)
            if len(str_value) > 500:
                raise ValidationError("metadata", "Metadata value too long (max 500 characters)", len(str_value))

            validated_metadata[key] = value

        return validated_metadata


async def validate_job_request(request: JobRequest) -> JobRequest:
    """Validate and sanitize job request."""
    try:
        # Validate query
        validated_query = JobRequestValidator.validate_query(request.query)

        # Validate agent type
        validated_agent_type = JobRequestValidator.validate_agent_type(request.agent_type)

        # Validate deep level
        validated_deep_level = JobRequestValidator.validate_deep_level(request.deep_level)

        # Validate priority
        validated_priority = JobRequestValidator.validate_priority(request.priority)

        # Validate tags
        validated_tags = JobRequestValidator.validate_tags(request.tags)

        # Validate metadata
        validated_metadata = JobRequestValidator.validate_metadata(request.metadata)

        # Return validated request
        return JobRequest(
            query=validated_query,
            agent_type=validated_agent_type,
            deep_level=validated_deep_level,
            priority=validated_priority,
            tags=validated_tags,
            metadata=validated_metadata
        )

    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "VALIDATION_ERROR",
                "message": e.message,
                "field": e.field,
                "value": e.value
            }
        )


async def validate_job_id(job_id: str) -> str:
    """Validate job ID format."""
    if not job_id:
        raise HTTPException(status_code=400, detail="Job ID is required")

    # Basic UUID format validation
    if not re.match(r"^[a-f0-9\-]{36}$", job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID format")

    return job_id


def setup_validation_middleware(app):
    """Setup validation middleware for the FastAPI app."""

    @app.middleware("http")
    async def validation_middleware(request: Request, call_next):
        """Request validation middleware."""
        try:
            return await rate_limit_middleware(request, call_next)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Validation middleware error: {e}")
            raise HTTPException(status_code=500, detail="Internal validation error")