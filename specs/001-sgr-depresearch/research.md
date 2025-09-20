# Research Findings: SGR Deep Research API Enhancement

## FastAPI Background Task Patterns for Long-Running Jobs

**Decision**: Use FastAPI Background Tasks with in-memory job tracking and optional Redis for scaling
**Rationale**:
- FastAPI Background Tasks provide simple async execution without external dependencies
- In-memory tracking sufficient for single-instance deployments
- Redis integration path available for multi-instance scaling
- Maintains existing deployment simplicity while enabling future growth

**Alternatives considered**:
- Celery: Too complex for current needs, requires message broker
- asyncio.create_task(): Limited lifecycle management, no persistence
- Direct threading: Poor integration with async FastAPI patterns

## Job Status Tracking and Polling Mechanisms

**Decision**: Hybrid approach with polling API + optional Server-Sent Events
**Rationale**:
- REST polling endpoints provide reliable status checking
- SSE enables real-time updates for web clients
- Both patterns supported simultaneously for different use cases
- Backward compatible with existing client patterns

**Alternatives considered**:
- WebSocket connections: More complex, requires connection management
- Pure polling: No real-time capability for responsive UIs
- Push notifications: Requires external infrastructure

## Non-Streaming API Design for Long-Running Operations

**Decision**: Job submission returns job_id immediately, separate status/result endpoints
**Rationale**:
- Immediate response prevents client timeouts
- Job ID enables resumable operations
- Clear separation of concerns (submit vs. monitor)
- Supports both fire-and-forget and monitoring workflows

**API Pattern**:
```
POST /jobs → {job_id, status: "pending"}
GET /jobs/{job_id} → {status, progress, result?, error?}
GET /jobs/{job_id}/stream → SSE updates
DELETE /jobs/{job_id} → cancel job
```

**Alternatives considered**:
- Long polling: Complex timeout management, poor user experience
- Callback URLs: Requires external webhooks, deployment complexity
- File-based communication: Poor real-time capability, cleanup issues

## Mock Testing Patterns for AI Agents and External APIs

**Decision**: Pytest fixtures with configurable mock responses for OpenAI/Tavily APIs
**Rationale**:
- Enables testing without external API dependencies
- Configurable responses test various scenarios (success, failure, timeout)
- Deterministic test outcomes regardless of external service status
- Cost-effective testing (no API charges)

**Mock Strategy**:
- httpx_mock for HTTP client mocking
- Pytest fixtures for reusable mock configurations
- Separate mock profiles for different test scenarios
- Integration with existing pytest infrastructure

**Alternatives considered**:
- Real API testing: Expensive, unreliable, environment dependent
- VCR.py cassettes: Complex setup, brittle to API changes
- Custom mock servers: Deployment overhead, maintenance burden

## Job Queue Implementation with Status Tracking

**Decision**: In-memory priority queue with persistent job metadata
**Rationale**:
- Python asyncio.Queue provides thread-safe operations
- Priority support enables urgent job processing
- Metadata persistence enables restart recovery
- Simple implementation, no external dependencies

**Implementation approach**:
- asyncio.PriorityQueue for job ordering
- SQLite/JSON file for job metadata persistence
- Background worker coroutines for job processing
- Graceful shutdown with job state preservation

**Alternatives considered**:
- Redis queues: Additional infrastructure requirement
- Database queues: Overkill for current scale
- File-based queues: Race condition complexity

## Server-Sent Events for Real-Time Updates

**Decision**: FastAPI SSE endpoints with job event streaming
**Rationale**:
- Native browser support, no additional client libraries
- Simple server implementation with FastAPI
- One-way communication sufficient for status updates
- Automatic reconnection handling in browsers

**Event format**:
```
event: job_progress
data: {"job_id": "123", "progress": 45, "status": "running"}

event: job_complete
data: {"job_id": "123", "status": "completed", "result_url": "/jobs/123"}
```

**Alternatives considered**:
- WebSockets: Bidirectional overhead not needed
- Long polling: More complex client implementation
- Push notifications: External service dependencies