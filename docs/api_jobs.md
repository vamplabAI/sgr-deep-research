# SGR Deep Research Jobs API Documentation

## Overview

The SGR Deep Research Jobs API provides asynchronous job management for long-running research operations. This API allows you to submit research jobs, monitor their progress, and retrieve results without blocking HTTP connections.

## Base URL

```
http://localhost:8010
```

## Authentication

Currently, no authentication is required for local development. Production deployments should implement appropriate authentication mechanisms.

## API Endpoints

### 1. Submit Job

Submit a new research job for asynchronous execution.

**Endpoint:** `POST /jobs`

**Request Body:**
```json
{
  "query": "Research question or topic to investigate",
  "agent_type": "sgr-tools",
  "deep_level": 0,
  "priority": 0,
  "tags": ["optional", "tags"],
  "metadata": {
    "optional": "metadata"
  }
}
```

**Request Parameters:**
- `query` (string, required): Research question, 1-1000 characters
- `agent_type` (string, required): Agent type - one of: `sgr`, `sgr-tools`, `sgr-auto-tools`, `sgr-so-tools`, `tools`
- `deep_level` (integer, optional): Research depth level, 0-10 (default: 0)
- `priority` (integer, optional): Job priority, -100 to 100 (default: 0)
- `tags` (array, optional): User-defined tags, max 10 items
- `metadata` (object, optional): Additional configuration parameters

**Response (201 Created):**
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "created_at": "2024-01-21T10:30:00Z",
  "estimated_completion": "2024-01-21T11:30:00Z"
}
```

**Error Responses:**
- `400 Bad Request`: Invalid request parameters
- `429 Too Many Requests`: Queue is full

### 2. Get Job Status

Retrieve current status and results for a specific job.

**Endpoint:** `GET /jobs/{job_id}`

**Path Parameters:**
- `job_id` (string, required): Unique job identifier (UUID)

**Response (200 OK):**
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "progress": 100.0,
  "current_step": "Job completed successfully",
  "steps_completed": 20,
  "total_steps": 20,
  "created_at": "2024-01-21T10:30:00Z",
  "started_at": "2024-01-21T10:30:05Z",
  "completed_at": "2024-01-21T11:15:30Z",
  "result": {
    "final_answer": "Generated research report content",
    "report_url": "/jobs/123e4567-e89b-12d3-a456-426614174000/report",
    "sources": [
      {
        "number": 1,
        "url": "https://example.com/article",
        "title": "Research Article Title",
        "confidence_score": 0.95
      }
    ],
    "metrics": {
      "total_duration_seconds": 1845.5,
      "api_calls_made": 25,
      "tokens_consumed": 15000,
      "estimated_cost_usd": 2.45,
      "search_operations": 8
    }
  },
  "error": null
}
```

**Job Status Values:**
- `pending`: Job is queued and waiting for execution
- `running`: Job is currently being executed
- `completed`: Job completed successfully
- `failed`: Job failed with an error
- `cancelled`: Job was cancelled by user

**Error Responses:**
- `404 Not Found`: Job not found

### 3. List Jobs

Retrieve a list of jobs with optional filtering.

**Endpoint:** `GET /jobs`

**Query Parameters:**
- `status` (string, optional): Filter by job status
- `limit` (integer, optional): Maximum number of jobs to return, 1-100 (default: 20)
- `offset` (integer, optional): Number of jobs to skip for pagination (default: 0)
- `tags` (string, optional): Filter by tags (comma-separated)

**Response (200 OK):**
```json
{
  "jobs": [
    {
      "job_id": "123e4567-e89b-12d3-a456-426614174000",
      "status": "completed",
      "progress": 100.0,
      "query": "Research question...",
      "agent_type": "sgr-tools",
      "tags": ["ai", "research"],
      "created_at": "2024-01-21T10:30:00Z",
      "completed_at": "2024-01-21T11:15:30Z"
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

### 4. Cancel Job

Cancel a pending or running job.

**Endpoint:** `DELETE /jobs/{job_id}`

**Path Parameters:**
- `job_id` (string, required): Unique job identifier

**Response (200 OK):**
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "cancelled",
  "cancelled_at": "2024-01-21T10:45:00Z",
  "message": "Job cancelled successfully"
}
```

**Error Responses:**
- `404 Not Found`: Job not found
- `409 Conflict`: Job cannot be cancelled (already completed)

### 5. Stream Job Updates

Server-Sent Events endpoint for real-time job progress updates.

**Endpoint:** `GET /jobs/{job_id}/stream`

**Path Parameters:**
- `job_id` (string, required): Unique job identifier

**Response (200 OK):**
```
Content-Type: text/event-stream

event: job_progress
data: {"job_id": "123e4567-e89b-12d3-a456-426614174000", "progress": 45.5, "current_step": "Analyzing sources"}

event: job_complete
data: {"job_id": "123e4567-e89b-12d3-a456-426614174000", "status": "completed"}
```

**Event Types:**
- `job_status`: Initial job status
- `job_progress`: Progress updates during execution
- `job_complete`: Job completion notification
- `error`: Error messages

**Error Responses:**
- `404 Not Found`: Job not found

## Data Models

### JobRequest
```json
{
  "query": "string (1-1000 chars)",
  "agent_type": "enum: sgr|sgr-tools|sgr-auto-tools|sgr-so-tools|tools",
  "deep_level": "integer (0-10, default: 0)",
  "priority": "integer (-100 to 100, default: 0)",
  "tags": "array of strings (max 10 items)",
  "metadata": "object (additional parameters)"
}
```

### JobStatus
```json
{
  "job_id": "string (UUID)",
  "status": "enum: pending|running|completed|failed|cancelled",
  "progress": "number (0.0-100.0)",
  "current_step": "string",
  "steps_completed": "integer",
  "total_steps": "integer",
  "created_at": "string (ISO 8601)",
  "started_at": "string (ISO 8601, nullable)",
  "completed_at": "string (ISO 8601, nullable)"
}
```

### JobResult
```json
{
  "final_answer": "string",
  "report_url": "string (nullable)",
  "sources": [
    {
      "number": "integer",
      "url": "string",
      "title": "string",
      "content_excerpt": "string",
      "confidence_score": "number (0.0-1.0)"
    }
  ],
  "metrics": {
    "total_duration_seconds": "number",
    "api_calls_made": "integer",
    "tokens_consumed": "integer",
    "estimated_cost_usd": "number",
    "search_operations": "integer"
  }
}
```

### JobError
```json
{
  "error_type": "enum: network|timeout|validation|resource|internal",
  "error_message": "string",
  "error_details": "object",
  "retry_count": "integer",
  "is_retryable": "boolean",
  "occurred_at": "string (ISO 8601)"
}
```

## Error Handling

### Standard Error Response Format
```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": {
    "field": "validation_field",
    "constraint": "validation_constraint"
  },
  "timestamp": "2024-01-21T10:30:00Z"
}
```

### Common Error Codes
- `INVALID_REQUEST`: Request validation failed
- `JOB_NOT_FOUND`: Requested job does not exist
- `QUEUE_FULL`: Job queue is at capacity
- `VALIDATION_ERROR`: Request parameters are invalid
- `INTERNAL_SERVER_ERROR`: Unexpected server error

## Rate Limiting

The API implements rate limiting to prevent abuse:
- **Limit**: 10 requests per 5-minute window per IP
- **Headers**: Rate limit information is returned in response headers
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Remaining requests in window
  - `X-RateLimit-Reset`: Time when window resets

When rate limit is exceeded:
```json
HTTP 429 Too Many Requests
{
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Rate limit exceeded. Too many requests.",
  "details": {
    "limit": 10,
    "window_minutes": 5
  }
}
```

## Usage Examples

### Python Client Example
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

    # Monitor progress
    while True:
        response = await client.get(f"http://localhost:8010/jobs/{job_id}")
        job_status = response.json()

        print(f"Status: {job_status['status']}, Progress: {job_status['progress']}%")

        if job_status["status"] in ["completed", "failed", "cancelled"]:
            break

        await asyncio.sleep(5)

    await client.aclose()

# Run the example
asyncio.run(submit_and_monitor_job())
```

### cURL Examples

Submit a job:
```bash
curl -X POST http://localhost:8010/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Analyze recent developments in quantum computing",
    "agent_type": "sgr-tools"
  }'
```

Check job status:
```bash
curl http://localhost:8010/jobs/123e4567-e89b-12d3-a456-426614174000
```

Stream job updates:
```bash
curl -N http://localhost:8010/jobs/123e4567-e89b-12d3-a456-426614174000/stream
```

List jobs:
```bash
curl "http://localhost:8010/jobs?status=running&limit=10"
```

Cancel a job:
```bash
curl -X DELETE http://localhost:8010/jobs/123e4567-e89b-12d3-a456-426614174000
```

## Integration with Existing API

The new Jobs API works alongside the existing OpenAI-compatible streaming API:

- **Use streaming API** (`/v1/chat/completions`) for:
  - Quick interactive queries (< 5 minutes)
  - Real-time development and testing
  - Integration with existing OpenAI client libraries

- **Use Jobs API** (`/jobs`) for:
  - Long-running research (> 10 minutes)
  - Batch processing workflows
  - Applications requiring job persistence
  - Multi-user environments with queue management

Both APIs use the same underlying SGR agents and maintain consistent research quality.

## Production Considerations

### Security
- Implement authentication and authorization
- Add input validation and sanitization
- Configure CORS policies appropriately
- Enable HTTPS in production

### Scalability
- Consider Redis for job queue persistence
- Implement horizontal scaling with load balancers
- Add database persistence for job history
- Monitor resource usage and set appropriate limits

### Monitoring
- Add application performance monitoring (APM)
- Set up logging and alerting for job failures
- Monitor queue sizes and processing times
- Track API usage patterns and performance metrics

### Deployment
- Use containerization (Docker) for consistent deployments
- Implement health checks and readiness probes
- Configure resource limits and auto-scaling
- Set up backup and disaster recovery procedures