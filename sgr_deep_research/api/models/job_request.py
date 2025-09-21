"""JobRequest Pydantic model for job submission.

This module defines the JobRequest model used for submitting new research jobs
to the SGR Deep Research system.
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum


class AgentType(str, Enum):
    """Available agent types for job execution."""
    SGR = "sgr"
    SGR_TOOLS = "sgr-tools"
    SGR_AUTO_TOOLS = "sgr-auto-tools"
    SGR_SO_TOOLS = "sgr-so-tools"
    TOOLS = "tools"


class JobRequest(BaseModel):
    """Request model for submitting a new research job.

    This model captures all parameters needed to submit a long-running research job
    and validates the input according to system constraints.
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Research question or topic to investigate"
    )

    agent_type: AgentType = Field(
        default=AgentType.SGR_TOOLS,
        description="Agent type to use for research execution"
    )

    deep_level: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Research depth level (0-10, higher = more comprehensive)"
    )

    priority: int = Field(
        default=0,
        ge=-100,
        le=100,
        description="Job priority for queue ordering (higher = more urgent)"
    )

    tags: List[str] = Field(
        default_factory=list,
        max_items=10,
        description="User-defined tags for organization and filtering"
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional configuration parameters"
    )

    max_iterations: Optional[int] = Field(
        default=None,
        ge=1,
        le=200,
        description="Maximum research steps (auto-calculated from deep_level if not provided)"
    )

    max_searches: Optional[int] = Field(
        default=None,
        ge=1,
        le=100,
        description="Maximum search operations (auto-calculated from deep_level if not provided)"
    )

    timeout_minutes: Optional[int] = Field(
        default=None,
        ge=1,
        le=480,  # 8 hours max
        description="Maximum execution time in minutes"
    )

    @validator('query')
    def validate_query(cls, v):
        """Validate query content."""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty or whitespace only")

        # Remove excessive whitespace
        v = ' '.join(v.split())

        # Basic content validation
        if len(v) < 3:
            raise ValueError("Query must be at least 3 characters long")

        return v

    @validator('tags')
    def validate_tags(cls, v):
        """Validate and normalize tags."""
        if not v:
            return []

        normalized_tags = []
        for tag in v:
            if isinstance(tag, str):
                # Normalize tag: strip whitespace, convert to lowercase
                normalized_tag = tag.strip().lower()
                if normalized_tag and len(normalized_tag) <= 50:
                    normalized_tags.append(normalized_tag)

        # Remove duplicates while preserving order
        seen = set()
        unique_tags = []
        for tag in normalized_tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)

        return unique_tags

    @validator('metadata')
    def validate_metadata(cls, v):
        """Validate metadata content and size."""
        if not v:
            return {}

        # Check total metadata size (rough estimate)
        import json
        try:
            metadata_str = json.dumps(v)
            if len(metadata_str) > 10000:  # 10KB limit
                raise ValueError("Metadata size exceeds 10KB limit")
        except (TypeError, ValueError) as e:
            if "Metadata size exceeds" in str(e):
                raise e
            raise ValueError("Metadata must be JSON serializable")

        return v

    def calculate_iterations_and_searches(self) -> tuple[int, int]:
        """Calculate max_iterations and max_searches based on deep_level.

        Returns:
            tuple: (max_iterations, max_searches)
        """
        if self.deep_level == 0:
            # Standard research mode
            iterations = 6
            searches = 4
        else:
            # Deep research mode with exponential scaling
            iterations = 6 * (3 * self.deep_level + 1)
            searches = 4 * (self.deep_level + 1)

        return iterations, searches

    def get_effective_iterations(self) -> int:
        """Get effective max_iterations (provided or calculated)."""
        if self.max_iterations is not None:
            return self.max_iterations

        iterations, _ = self.calculate_iterations_and_searches()
        return iterations

    def get_effective_searches(self) -> int:
        """Get effective max_searches (provided or calculated)."""
        if self.max_searches is not None:
            return self.max_searches

        _, searches = self.calculate_iterations_and_searches()
        return searches

    def get_estimated_duration_minutes(self) -> int:
        """Estimate job duration in minutes based on parameters."""
        base_minutes = 2  # Base time for simple query

        # Scale with deep level
        if self.deep_level > 0:
            base_minutes *= (2 ** self.deep_level)

        # Scale with iterations
        iterations = self.get_effective_iterations()
        base_minutes += (iterations * 0.5)  # ~30 seconds per iteration

        # Scale with searches
        searches = self.get_effective_searches()
        base_minutes += (searches * 1.0)  # ~1 minute per search

        return max(1, int(base_minutes))

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"  # Prevent extra fields
        schema_extra = {
            "example": {
                "query": "What are the latest developments in AI research?",
                "agent_type": "sgr-tools",
                "deep_level": 1,
                "priority": 0,
                "tags": ["ai", "research", "trends"],
                "metadata": {
                    "department": "research",
                    "project": "ai-analysis"
                }
            }
        }