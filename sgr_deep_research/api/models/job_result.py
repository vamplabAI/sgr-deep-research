"""JobResult Pydantic model for completed job results.

This module defines the JobResult model used for storing and retrieving
the final output and metadata from completed research jobs.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from decimal import Decimal

from .research_source import ResearchSource
from .execution_metrics import ExecutionMetrics


class FileArtifact(BaseModel):
    """File artifact generated during job execution."""

    file_path: str = Field(
        ...,
        description="Relative path to the generated file"
    )

    file_type: str = Field(
        ...,
        description="MIME type or file category"
    )

    size_bytes: int = Field(
        ...,
        ge=0,
        description="File size in bytes"
    )

    description: str = Field(
        ...,
        max_length=200,
        description="Human-readable description of the file"
    )

    created_at: datetime = Field(
        ...,
        description="File creation timestamp"
    )

    checksum: Optional[str] = Field(
        default=None,
        description="File checksum for integrity verification"
    )

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "file_path": "reports/job_123/research_report.md",
                "file_type": "text/markdown",
                "size_bytes": 15420,
                "description": "Comprehensive research report",
                "created_at": "2024-01-21T10:45:00Z",
                "checksum": "sha256:abc123..."
            }
        }


class JobResult(BaseModel):
    """Result model for completed research jobs.

    This model contains the final output and comprehensive metadata
    from successfully completed research jobs.
    """

    job_id: str = Field(
        ...,
        pattern=r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        description="Reference to the originating job"
    )

    final_answer: str = Field(
        ...,
        min_length=1,
        description="Generated research report content"
    )

    report_path: Optional[str] = Field(
        default=None,
        description="File path to saved markdown report"
    )

    sources: List[ResearchSource] = Field(
        default_factory=list,
        description="All sources used during research"
    )

    metrics: ExecutionMetrics = Field(
        ...,
        description="Performance and cost statistics"
    )

    agent_conversation: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Full agent conversation history"
    )

    artifacts: List[FileArtifact] = Field(
        default_factory=list,
        description="Generated files and attachments"
    )

    # Summary statistics
    quality_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=10.0,
        description="Research quality score (0-10)"
    )

    research_depth: Optional[int] = Field(
        default=None,
        ge=0,
        description="Achieved research depth level"
    )

    key_insights: List[str] = Field(
        default_factory=list,
        max_items=20,
        description="Key insights extracted from research"
    )

    # Technical metadata
    agent_version: Optional[str] = Field(
        default=None,
        description="Version of the agent used for research"
    )

    completion_reason: str = Field(
        default="success",
        description="Reason for job completion"
    )

    warnings: List[str] = Field(
        default_factory=list,
        description="Non-fatal warnings encountered during execution"
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Result creation timestamp"
    )

    @field_validator('final_answer')
    @classmethod
    def validate_final_answer(cls, v):
        """Validate final answer content."""
        if not v or not v.strip():
            raise ValueError("final_answer cannot be empty")

        # Check minimum content length
        if len(v.strip()) < 50:
            raise ValueError("final_answer must be at least 50 characters")

        return v.strip()

    @field_validator('sources')
    @classmethod
    def validate_sources(cls, v):
        """Validate sources list."""
        if not v:
            return []

        # Check for duplicate URLs
        seen_urls = set()
        unique_sources = []

        for source in v:
            if source.url not in seen_urls:
                seen_urls.add(source.url)
                unique_sources.append(source)

        # Sort sources by number
        unique_sources.sort(key=lambda s: s.number)

        return unique_sources

    @field_validator('key_insights')
    @classmethod
    def validate_key_insights(cls, v):
        """Validate and clean key insights."""
        if not v:
            return []

        cleaned_insights = []
        for insight in v:
            if isinstance(insight, str) and insight.strip():
                # Limit insight length
                cleaned_insight = insight.strip()[:500]
                if cleaned_insight not in cleaned_insights:
                    cleaned_insights.append(cleaned_insight)

        return cleaned_insights

    @field_validator('agent_conversation')
    @classmethod
    def validate_agent_conversation(cls, v):
        """Validate agent conversation history."""
        if not v:
            return []

        # Validate conversation structure
        valid_conversation = []
        for entry in v:
            if isinstance(entry, dict) and 'role' in entry and 'content' in entry:
                valid_conversation.append(entry)

        return valid_conversation

    def get_source_count(self) -> int:
        """Get total number of sources used."""
        return len(self.sources)

    def get_unique_domains(self) -> List[str]:
        """Get list of unique domains from sources."""
        domains = set()
        for source in self.sources:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(source.url)
                if parsed.netloc:
                    domains.add(parsed.netloc.lower())
            except Exception:
                continue

        return sorted(domains)

    def get_total_file_size(self) -> int:
        """Get total size of all artifacts in bytes."""
        return sum(artifact.size_bytes for artifact in self.artifacts)

    def calculate_words_generated(self) -> int:
        """Calculate approximate word count of generated content."""
        if not self.final_answer:
            return 0

        # Simple word count
        words = len(self.final_answer.split())
        return words

    def get_research_efficiency_score(self) -> float:
        """Calculate research efficiency score based on sources and time."""
        if not self.sources or not self.metrics.total_duration_seconds:
            return 0.0

        # Score based on sources per minute
        duration_minutes = self.metrics.total_duration_seconds / 60
        sources_per_minute = len(self.sources) / duration_minutes

        # Normalize to 0-10 scale (assume 1 source per minute = score of 5)
        efficiency = min(10.0, sources_per_minute * 5.0)
        return round(efficiency, 2)

    def generate_summary(self, max_length: int = 200) -> str:
        """Generate a brief summary of the result."""
        if not self.final_answer:
            return "No content available"

        # Extract first paragraph or sentences up to max_length
        content = self.final_answer.strip()
        if len(content) <= max_length:
            return content

        # Find a good breaking point
        truncated = content[:max_length]
        last_period = truncated.rfind('.')
        last_space = truncated.rfind(' ')

        if last_period > max_length * 0.7:  # If period is reasonably close to end
            return content[:last_period + 1]
        elif last_space > max_length * 0.8:  # If space is close to end
            return content[:last_space] + "..."
        else:
            return truncated + "..."

    model_config = {
        "validate_assignment": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        },
        "json_schema_extra": {
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "final_answer": "Based on comprehensive research across 15 sources, the latest developments in AI research show significant progress in large language models, with particular advances in reasoning capabilities and multimodal integration...",
                "report_path": "reports/job_123/ai_research_report.md",
                "sources": [
                    {
                        "number": 1,
                        "url": "https://arxiv.org/abs/2024.12345",
                        "title": "Advances in Large Language Models",
                        "confidence_score": 0.92
                    }
                ],
                "metrics": {
                    "total_duration_seconds": 1800,
                    "api_calls_made": 45,
                    "tokens_consumed": 12500,
                    "estimated_cost": "2.35"
                },
                "quality_score": 8.5,
                "research_depth": 2,
                "key_insights": [
                    "LLMs show improved reasoning in complex scenarios",
                    "Multimodal capabilities are rapidly advancing"
                ],
                "completion_reason": "success"
            }
        }
    }