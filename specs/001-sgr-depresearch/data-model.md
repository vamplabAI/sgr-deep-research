# Data Model: SGR Deep Research Job Management

## Core Entities

### JobRequest
**Purpose**: Captures all parameters needed to submit a long-running research job
**Lifecycle**: Created on job submission, immutable after creation

**Attributes**:
- `query: str` - Research question or topic to investigate (min 1, max 1000 chars)
- `agent_type: AgentType` - Agent type enum (SGR, SGR_TOOLS, SGR_AUTO_TOOLS, etc.)
- `deep_level: int = 0` - Research depth level (0-10, higher = more comprehensive)
- `priority: int = 0` - Job priority for queue ordering (-100 to 100, higher = more urgent)
- `tags: List[str] = []` - User-defined tags for organization (max 10 items)
- `metadata: Dict[str, Any] = {}` - Additional configuration parameters (max 10KB JSON)
- `max_iterations: Optional[int]` - Maximum research steps (auto-calculated from deep_level if not provided)
- `max_searches: Optional[int]` - Maximum search operations (auto-calculated from deep_level if not provided)
- `timeout_minutes: Optional[int]` - Maximum execution time in minutes (1-480, max 8 hours)
- `job_id: str` - Auto-generated unique job identifier (UUID4 format)

**Validation Rules**:
- query: non-empty string, 3-1000 characters, whitespace normalized
- agent_type: must be valid registered agent from AgentType enum
- deep_level: 0-10 range (exponential scaling: steps = 6 × (3×level + 1))
- priority: -100 to 100 range for queue ordering
- tags: max 10 items, each max 50 chars, normalized to lowercase
- metadata: must be JSON serializable, max 10KB size limit

### JobStatus
**Purpose**: Tracks current state and progress of a running job
**Lifecycle**: Created when job starts, updated throughout execution, preserved after completion

**Attributes**:
- `job_id: str` - Unique identifier (UUID4)
- `status: JobState` - Current job state (pending, running, completed, failed, cancelled)
- `progress: float = 0.0` - Completion percentage (0.0-100.0)
- `current_step: str = ""` - Description of current operation
- `steps_completed: int = 0` - Number of steps finished
- `total_steps: int` - Estimated total steps (may adjust during execution)
- `searches_used: int = 0` - Number of search operations performed
- `sources_found: int = 0` - Number of sources discovered
- `created_at: datetime` - Job submission timestamp
- `started_at: Optional[datetime]` - Job execution start time
- `completed_at: Optional[datetime]` - Job completion/failure time
- `estimated_completion: Optional[datetime]` - Projected finish time

**State Transitions**:
- pending → running (when worker picks up job)
- running → completed (successful finish)
- running → failed (error occurred)
- running → cancelled (user cancellation)
- pending → cancelled (cancelled before execution)

### JobResult
**Purpose**: Contains final output and metadata from completed job
**Lifecycle**: Created when job completes successfully, immutable after creation

**Attributes**:
- `job_id: str` - Reference to originating job
- `final_answer: str` - Generated research report content
- `report_path: Optional[str]` - File path to saved report
- `sources: List[ResearchSource]` - All sources used in research
- `metrics: ExecutionMetrics` - Performance and cost statistics
- `agent_conversation: List[Dict]` - Full agent conversation history
- `artifacts: List[FileArtifact]` - Generated files and attachments

**Relationships**:
- One-to-one with JobStatus via job_id
- Contains collection of ResearchSource entities
- Contains ExecutionMetrics entity

### JobError
**Purpose**: Captures error information when jobs fail
**Lifecycle**: Created when job encounters unrecoverable error

**Attributes**:
- `job_id: str` - Reference to failed job
- `error_type: str` - Error classification (network, timeout, validation, etc.)
- `error_message: str` - Human-readable error description
- `error_details: Dict[str, Any]` - Technical error information
- `retry_count: int = 0` - Number of retry attempts made
- `is_retryable: bool` - Whether job can be automatically retried
- `occurred_at: datetime` - Error timestamp

### ResearchSource
**Purpose**: Represents a source used during research
**Lifecycle**: Created during research execution, associated with job result

**Attributes**:
- `number: int` - Sequential source number within job (≥1)
- `url: str` - Source URL or identifier (max 2000 chars, auto-prefix https://)
- `title: str` - Source title or description (max 500 chars, cleaned)
- `content_excerpt: str` - Relevant excerpt from source (max 2000 chars)
- `confidence_score: float` - Relevance confidence score (0.0-1.0)
- `source_type: SourceType` - Type/category (web_page, academic_paper, etc.)
- `status: SourceStatus` - Processing status (discovered, processing, analyzed, failed, skipped)
- `discovered_at: datetime` - Timestamp when source was discovered
- `analyzed_at: Optional[datetime]` - Timestamp when source was analyzed
- `word_count: Optional[int]` - Word count of analyzed content
- `language: Optional[str]` - Detected language code (e.g., 'en', 'es')
- `author: Optional[str]` - Author name if available (max 200 chars)
- `publication_date: Optional[datetime]` - Publication date if available
- `domain: Optional[str]` - Source domain extracted from URL (max 200 chars)
- `key_topics: List[str]` - Key topics identified in source (max 20 items)
- `relevance_keywords: List[str]` - Keywords that made source relevant (max 50 items)
- `processing_time_ms: Optional[float]` - Time taken to process source in milliseconds
- `error_message: Optional[str]` - Error message if processing failed (max 500 chars)
- `citation_format: Optional[str]` - Formatted citation for the source
- `access_date: datetime` - Date when source was accessed

**Methods**:
- `extract_domain() -> str` - Extract domain from URL
- `calculate_relevance_score(query_keywords) -> float` - Calculate relevance based on keyword matching
- `generate_citation(style="apa") -> str` - Generate formatted citation
- `is_academic_source() -> bool` - Check if source appears to be academic

### ExecutionMetrics
**Purpose**: Performance and resource usage statistics for completed jobs
**Lifecycle**: Accumulated during job execution, finalized at completion

**Attributes**:
- `total_duration_seconds: float` - Wall clock execution time in seconds
- `queue_time_seconds: float` - Time spent waiting in queue
- `execution_time_seconds: float` - Actual execution time (excluding queue)
- `api_calls_made: int` - Total number of external API calls
- `openai_calls: int` - Number of OpenAI API calls
- `tavily_calls: int` - Number of Tavily search API calls
- `tokens_consumed: int` - Total LLM tokens consumed
- `input_tokens: int` - Input tokens sent to LLM
- `output_tokens: int` - Output tokens generated by LLM
- `estimated_cost: Decimal` - Total estimated execution cost in USD
- `cost_breakdown: CostBreakdown` - Detailed cost breakdown by service
- `peak_memory_mb: int` - Peak memory usage in megabytes
- `avg_cpu_percent: Optional[float]` - Average CPU utilization percentage
- `disk_io_operations: int` - Number of disk I/O operations
- `network_bytes_transferred: int` - Total network bytes transferred
- `search_operations: int` - Number of search operations performed
- `sources_processed: int` - Number of sources analyzed
- `retry_operations: int` - Number of retry attempts made
- `research_depth_achieved: int` - Actual research depth level achieved
- `quality_score: Optional[float]` - Research quality score (0-10)
- `completeness_score: Optional[float]` - Research completeness score (0.0-1.0)
- `performance: PerformanceMetrics` - Detailed performance metrics
- `started_at: datetime` - Execution start timestamp
- `completed_at: datetime` - Execution completion timestamp
- `agent_version: Optional[str]` - Version of the agent used
- `system_info: Dict[str, Any]` - System information during execution

## Supporting Entities

### CostBreakdown
**Purpose**: Detailed cost breakdown by service for financial tracking
**Lifecycle**: Accumulated during job execution, finalized at completion

**Attributes**:
- `openai_cost: Decimal` - Cost for OpenAI API calls
- `tavily_cost: Decimal` - Cost for Tavily search API calls
- `other_api_costs: Dict[str, Decimal]` - Costs for other API services
- `compute_cost: Decimal` - Estimated compute/infrastructure cost

**Methods**:
- `get_total_cost() -> Decimal` - Calculate total cost across all services

### PerformanceMetrics
**Purpose**: Performance metrics for execution analysis and optimization
**Lifecycle**: Collected during job execution, used for system optimization

**Attributes**:
- `avg_response_time_ms: Optional[float]` - Average API response time in milliseconds
- `cache_hit_rate: Optional[float]` - Cache hit rate (0.0-1.0)
- `concurrent_operations: int` - Peak concurrent operations
- `queue_wait_time_seconds: Optional[float]` - Time spent waiting in queue
- `execution_efficiency: Optional[float]` - Execution efficiency score (0.0-1.0)

### JobQueue
**Purpose**: Manages job prioritization and concurrency control
**Lifecycle**: Persistent system component

**Attributes**:
- `pending_jobs: PriorityQueue[JobRequest]` - Jobs awaiting execution
- `running_jobs: Dict[str, JobStatus]` - Currently executing jobs
- `max_concurrent_jobs: int` - Concurrency limit
- `current_load: float` - System load metric (0.0-1.0)

### FileArtifact
**Purpose**: Represents files generated during job execution
**Lifecycle**: Created during job execution, preserved with results

**Attributes**:
- `file_path: str` - Relative path to file
- `file_type: str` - MIME type or file category
- `size_bytes: int` - File size
- `description: str` - Human-readable description
- `created_at: datetime` - File creation timestamp

## Entity Relationships

```
JobRequest (1) ←→ (1) JobStatus
JobStatus (1) ←→ (0..1) JobResult
JobStatus (1) ←→ (0..1) JobError
JobResult (1) ←→ (*) ResearchSource
JobResult (1) ←→ (1) ExecutionMetrics
JobResult (1) ←→ (*) FileArtifact
JobQueue (1) ←→ (*) JobRequest
JobQueue (1) ←→ (*) JobStatus
```

## Data Persistence

**In-Memory Storage** (default):
- JobQueue: Python asyncio.PriorityQueue
- Active jobs: Dict[str, JobStatus]
- Recent results: LRU cache with configurable size

**File-Based Persistence**:
- Job metadata: JSON files in jobs/ directory
- Completed results: Markdown files in reports/ directory
- Error logs: JSON files in errors/ directory

**Future Redis Storage** (optional scaling):
- Job queue: Redis sorted sets for priority ordering
- Job status: Redis hashes with TTL for cleanup
- Results: Redis strings with compression for large content