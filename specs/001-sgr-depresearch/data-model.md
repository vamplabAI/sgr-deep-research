# Data Model: SGR Deep Research Job Management

## Core Entities

### JobRequest
**Purpose**: Captures all parameters needed to submit a long-running research job
**Lifecycle**: Created on job submission, immutable after creation

**Attributes**:
- `query: str` - Research question or topic to investigate
- `agent_type: str` - Agent type (sgr, sgr-tools, sgr-auto-tools, etc.)
- `deep_level: int = 0` - Research depth level (0-5+)
- `max_iterations: int` - Maximum research steps (calculated from deep_level)
- `max_searches: int` - Maximum search operations (calculated from deep_level)
- `priority: int = 0` - Job priority for queue ordering (higher = more urgent)
- `tags: List[str] = []` - User-defined tags for organization
- `metadata: Dict[str, Any] = {}` - Additional configuration parameters

**Validation Rules**:
- query must be non-empty string, max 1000 characters
- agent_type must be valid registered agent
- deep_level must be 0-10 (practical limit)
- priority must be -100 to 100 range

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
- `number: int` - Sequential source number within job
- `url: str` - Source URL or identifier
- `title: str` - Source title or description
- `content_excerpt: str` - Relevant excerpt from source
- `confidence_score: float` - Relevance confidence (0.0-1.0)
- `discovered_at: datetime` - When source was found

### ExecutionMetrics
**Purpose**: Performance and resource usage statistics for completed jobs
**Lifecycle**: Accumulated during job execution, finalized at completion

**Attributes**:
- `total_duration: timedelta` - Wall clock execution time
- `api_calls_made: int` - Number of external API calls
- `tokens_consumed: int` - Total LLM tokens used
- `estimated_cost: Decimal` - Estimated execution cost
- `peak_memory_mb: int` - Maximum memory usage
- `search_operations: int` - Number of search operations
- `retry_operations: int` - Number of retry attempts

## Supporting Entities

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