# Quickstart: SGR Deep Research Jobs API

## Overview
This guide demonstrates how to use the new asynchronous jobs API for long-running research operations. The API allows you to submit research jobs and monitor their progress without blocking HTTP connections.

## Prerequisites
- SGR Deep Research system running on `localhost:8010`
- API client (curl, httpx, requests, etc.)
- Valid agent configuration (see existing AGENTS.md)

## Basic Workflow

### 1. Submit a Research Job

Submit a new research job and get immediate response with job ID:

```bash
curl -X POST http://localhost:8010/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Analyze recent developments in quantum computing",
    "agent_type": "sgr-tools"
  }'
```

Expected response:
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "created_at": "2024-01-21T10:30:00Z",
  "estimated_completion": "2024-01-21T10:35:00Z"
}
```

### 2. Check Job Status

Poll the job status to monitor progress:

```bash
curl http://localhost:8010/jobs/123e4567-e89b-12d3-a456-426614174000
```

Response during execution:
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "running",
  "progress": 45.5,
  "current_step": "Analyzing research sources",
  "steps_completed": 9,
  "total_steps": 20,
  "created_at": "2024-01-21T10:30:00Z",
  "started_at": "2024-01-21T10:30:05Z",
  "result": null,
  "error": null
}
```

### 3. Retrieve Results

When job completes (status = "completed"), get the full results:

```bash
curl http://localhost:8010/jobs/123e4567-e89b-12d3-a456-426614174000
```

Response with results:
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "progress": 100.0,
  "completed_at": "2024-01-21T10:35:30Z",
  "result": {
    "final_answer": "# Quantum Computing Analysis\n\nRecent developments...",
    "report_url": "/jobs/123e4567-e89b-12d3-a456-426614174000/report",
    "sources": [
      {
        "number": 1,
        "url": "https://example.com/quantum-research",
        "title": "Latest Quantum Computing Breakthroughs",
        "confidence_score": 0.95
      }
    ],
    "metrics": {
      "total_duration_seconds": 325.5,
      "api_calls_made": 15,
      "tokens_consumed": 8500,
      "estimated_cost_usd": 1.25,
      "search_operations": 5
    }
  }
}
```

## Advanced Usage

### Deep Research Job

Submit a deep research job with higher priority:

```bash
curl -X POST http://localhost:8010/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Comprehensive analysis of AI market trends in 2024",
    "agent_type": "sgr-tools",
    "deep_level": 2,
    "priority": 10,
    "tags": ["ai", "market", "2024"],
    "metadata": {
      "department": "research",
      "project": "q1-analysis"
    }
  }'
```

### Real-time Updates with Server-Sent Events

Monitor job progress in real-time using SSE:

```bash
curl -N http://localhost:8010/jobs/123e4567-e89b-12d3-a456-426614174000/stream
```

Example SSE stream:
```
event: job_progress
data: {"job_id": "123e4567-e89b-12d3-a456-426614174000", "progress": 25.0, "current_step": "Searching for sources"}

event: job_progress
data: {"job_id": "123e4567-e89b-12d3-a456-426614174000", "progress": 50.0, "current_step": "Analyzing content"}

event: job_complete
data: {"job_id": "123e4567-e89b-12d3-a456-426614174000", "status": "completed"}
```

### List All Jobs

Retrieve a list of your jobs with filtering:

```bash
# All jobs
curl http://localhost:8010/jobs

# Filter by status
curl "http://localhost:8010/jobs?status=running&limit=10"

# Filter by tags
curl "http://localhost:8010/jobs?tags=ai,research&limit=20"
```

### Cancel a Running Job

Cancel a job that's no longer needed:

```bash
curl -X DELETE http://localhost:8010/jobs/123e4567-e89b-12d3-a456-426614174000
```

Response:
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "cancelled",
  "cancelled_at": "2024-01-21T10:32:00Z",
  "message": "Job cancelled successfully"
}
```

## Python Client Example

```python
import httpx
import asyncio
import json

async def submit_and_monitor_job():
    client = httpx.AsyncClient()

    # Submit job
    response = await client.post("http://localhost:8010/jobs", json={
        "query": "Research sustainable energy trends",
        "agent_type": "sgr-tools",
        "deep_level": 1
    })
    job_data = response.json()
    job_id = job_data["job_id"]
    print(f"Job submitted: {job_id}")

    # Monitor progress
    while True:
        response = await client.get(f"http://localhost:8010/jobs/{job_id}")
        job_status = response.json()

        print(f"Status: {job_status['status']}, Progress: {job_status['progress']}%")

        if job_status["status"] in ["completed", "failed", "cancelled"]:
            break

        await asyncio.sleep(5)  # Poll every 5 seconds

    # Get final results
    if job_status["status"] == "completed":
        print("Job completed successfully!")
        print(f"Report length: {len(job_status['result']['final_answer'])} characters")
        print(f"Sources found: {len(job_status['result']['sources'])}")
        print(f"Cost: ${job_status['result']['metrics']['estimated_cost_usd']}")
    else:
        print(f"Job failed: {job_status.get('error', {}).get('error_message', 'Unknown error')}")

    await client.aclose()

# Run the example
asyncio.run(submit_and_monitor_job())
```

## Error Handling

### Common Error Responses

**400 Bad Request** - Invalid parameters:
```json
{
  "error": "INVALID_REQUEST",
  "message": "The query field is required and cannot be empty",
  "details": {"field": "query", "constraint": "non_empty"}
}
```

**404 Not Found** - Job doesn't exist:
```json
{
  "error": "JOB_NOT_FOUND",
  "message": "Job with ID 123e4567-e89b-12d3-a456-426614174000 not found"
}
```

**429 Too Many Requests** - Queue is full:
```json
{
  "error": "QUEUE_FULL",
  "message": "Too many jobs in queue, please try again later",
  "details": {"queue_size": 100, "max_queue_size": 100}
}
```

### Job Execution Errors

When jobs fail, the error information is included in the job status:

```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "failed",
  "error": {
    "error_type": "network",
    "error_message": "Failed to connect to external research API after 3 retries",
    "retry_count": 3,
    "is_retryable": true,
    "occurred_at": "2024-01-21T10:35:00Z"
  }
}
```

## Integration with Existing API

The new jobs API works alongside the existing OpenAI-compatible streaming API:

- **Use streaming API** (`/v1/chat/completions`) for:
  - Quick interactive queries
  - Real-time development and testing
  - Integration with existing OpenAI client libraries

- **Use jobs API** (`/jobs`) for:
  - Long-running research (>10 minutes)
  - Batch processing workflows
  - Applications requiring job persistence
  - Multi-user environments with queue management

Both APIs use the same underlying SGR agents and maintain consistent research quality.