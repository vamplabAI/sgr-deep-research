"""ResearchSource Pydantic model for research sources.

This module defines the ResearchSource model used for representing
sources discovered and used during research jobs.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator, HttpUrl
from enum import Enum


class SourceType(str, Enum):
    """Types of research sources."""
    WEB_PAGE = "web_page"
    ACADEMIC_PAPER = "academic_paper"
    NEWS_ARTICLE = "news_article"
    BLOG_POST = "blog_post"
    DOCUMENTATION = "documentation"
    VIDEO = "video"
    PODCAST = "podcast"
    BOOK = "book"
    REPORT = "report"
    DATABASE = "database"
    API = "api"
    OTHER = "other"


class SourceStatus(str, Enum):
    """Status of source processing."""
    DISCOVERED = "discovered"
    PROCESSING = "processing"
    ANALYZED = "analyzed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ResearchSource(BaseModel):
    """Model representing a source used during research.

    This model captures information about sources discovered and analyzed
    during the research process, including their relevance and content.
    """

    number: int = Field(
        ...,
        ge=1,
        description="Sequential source number within the research job"
    )

    url: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Source URL or identifier"
    )

    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Source title or description"
    )

    content_excerpt: str = Field(
        default="",
        max_length=2000,
        description="Relevant excerpt from the source content"
    )

    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Relevance confidence score (0.0-1.0)"
    )

    source_type: SourceType = Field(
        default=SourceType.WEB_PAGE,
        description="Type/category of the source"
    )

    status: SourceStatus = Field(
        default=SourceStatus.DISCOVERED,
        description="Processing status of the source"
    )

    discovered_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when source was discovered"
    )

    analyzed_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when source was analyzed"
    )

    # Content analysis
    word_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Word count of analyzed content"
    )

    language: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=10,
        description="Detected language code (e.g., 'en', 'es')"
    )

    # Metadata
    author: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Author name if available"
    )

    publication_date: Optional[datetime] = Field(
        default=None,
        description="Publication date if available"
    )

    domain: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Source domain (extracted from URL)"
    )

    # Analysis results
    key_topics: List[str] = Field(
        default_factory=list,
        max_items=20,
        description="Key topics identified in the source"
    )

    relevance_keywords: List[str] = Field(
        default_factory=list,
        max_items=50,
        description="Keywords that made this source relevant"
    )

    # Technical metadata
    processing_time_ms: Optional[float] = Field(
        default=None,
        ge=0,
        description="Time taken to process this source in milliseconds"
    )

    error_message: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Error message if source processing failed"
    )

    # Citation information
    citation_format: Optional[str] = Field(
        default=None,
        description="Formatted citation for the source"
    )

    access_date: datetime = Field(
        default_factory=datetime.utcnow,
        description="Date when source was accessed"
    )

    @validator('url')
    def validate_url(cls, v):
        """Validate URL format and accessibility."""
        if not v or not v.strip():
            raise ValueError("URL cannot be empty")

        v = v.strip()

        # Basic URL validation
        if not (v.startswith('http://') or v.startswith('https://')):
            # If no protocol, assume https
            if not v.startswith('//'):
                v = 'https://' + v

        # Additional validation for common patterns
        if len(v) > 2000:
            raise ValueError("URL too long (max 2000 characters)")

        return v

    @validator('title')
    def validate_title(cls, v):
        """Validate and clean title."""
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")

        # Clean up title
        cleaned = ' '.join(v.split())

        # Remove common prefixes/suffixes
        prefixes_to_remove = ['PDF', '[PDF]', 'Download', 'Free']
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix + ' '):
                cleaned = cleaned[len(prefix):].strip()

        return cleaned[:500]  # Ensure length limit

    @validator('content_excerpt')
    def validate_content_excerpt(cls, v):
        """Validate and clean content excerpt."""
        if not v:
            return ""

        # Clean up excerpt
        cleaned = ' '.join(v.split())

        # Ensure it ends with proper punctuation for readability
        if cleaned and not cleaned.endswith(('.', '!', '?', '...')):
            if len(cleaned) == 2000:  # Truncated
                cleaned = cleaned.rstrip() + '...'

        return cleaned

    @validator('key_topics', 'relevance_keywords')
    def validate_string_lists(cls, v):
        """Validate and clean string lists."""
        if not v:
            return []

        cleaned = []
        for item in v:
            if isinstance(item, str) and item.strip():
                cleaned_item = item.strip().lower()[:100]  # Normalize and limit
                if cleaned_item not in cleaned:
                    cleaned.append(cleaned_item)

        return cleaned

    @validator('language')
    def validate_language(cls, v):
        """Validate language code format."""
        if v is None:
            return None

        # Basic language code validation (ISO 639-1 or similar)
        v = v.lower().strip()
        if len(v) < 2 or len(v) > 10:
            return None

        return v

    def extract_domain(self) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(self.url)
            domain = parsed.netloc.lower()
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception:
            return ""

    def update_domain(self) -> None:
        """Update domain field from URL."""
        self.domain = self.extract_domain()

    def calculate_relevance_score(self, query_keywords: List[str]) -> float:
        """Calculate relevance score based on keyword matching."""
        if not query_keywords:
            return self.confidence_score

        # Count keyword matches in title and excerpt
        title_lower = self.title.lower()
        excerpt_lower = self.content_excerpt.lower()

        matches = 0
        for keyword in query_keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in title_lower:
                matches += 2  # Title matches worth more
            if keyword_lower in excerpt_lower:
                matches += 1

        # Normalize score
        max_possible_matches = len(query_keywords) * 3
        keyword_score = min(1.0, matches / max_possible_matches) if max_possible_matches > 0 else 0.0

        # Combine with existing confidence score
        combined_score = (self.confidence_score + keyword_score) / 2
        return round(combined_score, 3)

    def generate_citation(self, style: str = "apa") -> str:
        """Generate citation for the source."""
        if style.lower() == "apa":
            citation_parts = []

            if self.author:
                citation_parts.append(f"{self.author}.")

            if self.publication_date:
                year = self.publication_date.year
                citation_parts.append(f"({year}).")

            citation_parts.append(f"{self.title}.")

            if self.domain:
                citation_parts.append(f"Retrieved from {self.domain}")

            citation = " ".join(citation_parts)
            return citation

        # Default simple citation
        return f"{self.title}. Retrieved from {self.url}"

    def mark_as_analyzed(self) -> None:
        """Mark source as analyzed and update timestamp."""
        self.status = SourceStatus.ANALYZED
        self.analyzed_at = datetime.utcnow()

    def mark_as_failed(self, error_message: str) -> None:
        """Mark source as failed with error message."""
        self.status = SourceStatus.FAILED
        self.error_message = error_message[:500]  # Limit error message length

    def is_academic_source(self) -> bool:
        """Check if source appears to be academic."""
        if self.source_type == SourceType.ACADEMIC_PAPER:
            return True

        # Check domain patterns
        academic_domains = ['arxiv.org', 'pubmed.ncbi.nlm.nih.gov', 'scholar.google.com',
                           'researchgate.net', 'ieee.org', 'acm.org']

        domain = self.extract_domain()
        return any(academic in domain for academic in academic_domains)

    def get_age_days(self) -> Optional[int]:
        """Get age of source in days from publication date."""
        if not self.publication_date:
            return None

        delta = datetime.utcnow() - self.publication_date
        return delta.days

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "number": 1,
                "url": "https://arxiv.org/abs/2024.12345",
                "title": "Advances in Large Language Models: A Comprehensive Survey",
                "content_excerpt": "This paper presents a comprehensive survey of recent advances in large language models, focusing on architectural improvements and training methodologies...",
                "confidence_score": 0.92,
                "source_type": "academic_paper",
                "status": "analyzed",
                "discovered_at": "2024-01-21T10:30:00Z",
                "analyzed_at": "2024-01-21T10:30:15Z",
                "word_count": 12500,
                "language": "en",
                "author": "Smith, J. et al.",
                "publication_date": "2024-01-15T00:00:00Z",
                "domain": "arxiv.org",
                "key_topics": ["language models", "neural networks", "AI"],
                "relevance_keywords": ["LLM", "GPT", "transformer"],
                "processing_time_ms": 2340.5
            }
        }