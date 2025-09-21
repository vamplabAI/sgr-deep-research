"""Server-Sent Events (SSE) streaming utilities for SGR Deep Research.

This module provides utilities for streaming real-time job progress updates
to clients using Server-Sent Events protocol.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)


class SSEEvent:
    """Represents a Server-Sent Event."""

    def __init__(self, data: Dict[str, Any], event: str = "message", id: Optional[str] = None):
        self.data = data
        self.event = event
        self.id = id
        self.timestamp = datetime.now()

    def format(self) -> str:
        """Format the event for SSE transmission."""
        lines = []

        if self.id:
            lines.append(f"id: {self.id}")

        if self.event:
            lines.append(f"event: {self.event}")

        # Format data as JSON
        data_json = json.dumps(self.data)
        lines.append(f"data: {data_json}")

        # Add empty line to separate events
        lines.append("")

        return "\n".join(lines) + "\n"


class SSEStreamManager:
    """Manages SSE streams for multiple clients and jobs."""

    def __init__(self):
        self._streams: Dict[str, List[asyncio.Queue]] = {}
        self._stream_lock = asyncio.Lock()

    async def add_stream(self, job_id: str) -> asyncio.Queue:
        """Add a new SSE stream for a job."""
        stream_queue = asyncio.Queue(maxsize=100)  # Buffer up to 100 events

        async with self._stream_lock:
            if job_id not in self._streams:
                self._streams[job_id] = []
            self._streams[job_id].append(stream_queue)

        logger.debug(f"Added SSE stream for job {job_id}")
        return stream_queue

    async def remove_stream(self, job_id: str, stream_queue: asyncio.Queue):
        """Remove an SSE stream for a job."""
        async with self._stream_lock:
            if job_id in self._streams and stream_queue in self._streams[job_id]:
                self._streams[job_id].remove(stream_queue)
                if not self._streams[job_id]:
                    del self._streams[job_id]

        logger.debug(f"Removed SSE stream for job {job_id}")

    async def broadcast_event(self, job_id: str, event: SSEEvent):
        """Broadcast an event to all streams for a job."""
        async with self._stream_lock:
            streams = self._streams.get(job_id, [])

        if not streams:
            return

        # Send to all active streams
        for stream_queue in streams.copy():  # Copy to avoid modification during iteration
            try:
                stream_queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(f"SSE stream queue full for job {job_id}, dropping event")
            except Exception as e:
                logger.error(f"Error broadcasting to SSE stream for job {job_id}: {e}")

    async def broadcast_job_progress(
        self,
        job_id: str,
        progress: float,
        current_step: str = "",
        steps_completed: int = None,
        total_steps: int = None
    ):
        """Broadcast job progress update."""
        data = {
            "job_id": job_id,
            "progress": progress,
            "current_step": current_step,
            "timestamp": datetime.now().isoformat()
        }

        if steps_completed is not None:
            data["steps_completed"] = steps_completed
        if total_steps is not None:
            data["total_steps"] = total_steps

        event = SSEEvent(data=data, event="job_progress", id=f"{job_id}-{int(progress)}")
        await self.broadcast_event(job_id, event)

    async def broadcast_job_status_change(self, job_id: str, status: str, **kwargs):
        """Broadcast job status change."""
        data = {
            "job_id": job_id,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }

        event_type = f"job_{status}"
        event = SSEEvent(data=data, event=event_type, id=f"{job_id}-{status}")
        await self.broadcast_event(job_id, event)

    async def broadcast_job_error(self, job_id: str, error_message: str, error_type: str = "error"):
        """Broadcast job error."""
        data = {
            "job_id": job_id,
            "error_type": error_type,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat()
        }

        event = SSEEvent(data=data, event="job_error", id=f"{job_id}-error")
        await self.broadcast_event(job_id, event)

    def get_active_streams_count(self, job_id: str) -> int:
        """Get the number of active streams for a job."""
        return len(self._streams.get(job_id, []))

    def get_total_streams_count(self) -> int:
        """Get total number of active streams across all jobs."""
        return sum(len(streams) for streams in self._streams.values())


# Global SSE stream manager
_sse_manager: Optional[SSEStreamManager] = None


def get_sse_manager() -> SSEStreamManager:
    """Get the global SSE stream manager."""
    global _sse_manager
    if _sse_manager is None:
        _sse_manager = SSEStreamManager()
    return _sse_manager


async def create_job_stream(job_id: str, request: Request) -> StreamingResponse:
    """Create an SSE stream for a specific job."""
    sse_manager = get_sse_manager()

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events for the job."""
        stream_queue = await sse_manager.add_stream(job_id)

        try:
            # Send initial connection event
            initial_event = SSEEvent(
                data={"job_id": job_id, "message": "Connected to job stream"},
                event="stream_connected",
                id=f"{job_id}-connected"
            )
            yield initial_event.format()

            while True:
                try:
                    # Check if client disconnected
                    if await request.is_disconnected():
                        logger.debug(f"Client disconnected from job {job_id} stream")
                        break

                    # Wait for next event with timeout
                    event = await asyncio.wait_for(stream_queue.get(), timeout=30.0)
                    yield event.format()

                except asyncio.TimeoutError:
                    # Send keepalive event
                    keepalive_event = SSEEvent(
                        data={"type": "keepalive", "timestamp": datetime.now().isoformat()},
                        event="keepalive"
                    )
                    yield keepalive_event.format()

                except asyncio.CancelledError:
                    logger.debug(f"SSE stream cancelled for job {job_id}")
                    break

        except Exception as e:
            logger.error(f"Error in SSE stream for job {job_id}: {e}")
        finally:
            await sse_manager.remove_stream(job_id, stream_queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


class JobProgressTracker:
    """Tracks job progress and automatically broadcasts updates via SSE."""

    def __init__(self, job_id: str, total_steps: int = None):
        self.job_id = job_id
        self.total_steps = total_steps or 20
        self.current_step = 0
        self.progress = 0.0
        self.current_step_name = ""
        self.sse_manager = get_sse_manager()

    async def update_progress(
        self,
        progress: float = None,
        current_step_name: str = None,
        increment_step: bool = False
    ):
        """Update job progress and broadcast via SSE."""
        if increment_step:
            self.current_step += 1

        if progress is not None:
            self.progress = min(100.0, max(0.0, progress))
        else:
            # Calculate progress from current step
            self.progress = (self.current_step / self.total_steps) * 100.0

        if current_step_name is not None:
            self.current_step_name = current_step_name

        # Broadcast update
        await self.sse_manager.broadcast_job_progress(
            job_id=self.job_id,
            progress=self.progress,
            current_step=self.current_step_name,
            steps_completed=self.current_step,
            total_steps=self.total_steps
        )

    async def set_step(self, step_name: str, step_number: int = None):
        """Set current step and broadcast update."""
        if step_number is not None:
            self.current_step = step_number

        await self.update_progress(current_step_name=step_name)

    async def complete_step(self, step_name: str):
        """Mark current step as complete and move to next."""
        await self.update_progress(
            current_step_name=f"Completed: {step_name}",
            increment_step=True
        )

    async def finish(self, message: str = "Job completed"):
        """Mark job as finished."""
        self.progress = 100.0
        self.current_step_name = message

        await self.sse_manager.broadcast_job_progress(
            job_id=self.job_id,
            progress=100.0,
            current_step=message,
            steps_completed=self.total_steps,
            total_steps=self.total_steps
        )

        await self.sse_manager.broadcast_job_status_change(
            job_id=self.job_id,
            status="completed"
        )

    async def fail(self, error_message: str):
        """Mark job as failed."""
        await self.sse_manager.broadcast_job_error(
            job_id=self.job_id,
            error_message=error_message
        )

        await self.sse_manager.broadcast_job_status_change(
            job_id=self.job_id,
            status="failed",
            error_message=error_message
        )


@asynccontextmanager
async def track_job_progress(job_id: str, total_steps: int = None):
    """Context manager for tracking job progress with automatic SSE updates."""
    tracker = JobProgressTracker(job_id, total_steps)

    try:
        # Send job started event
        await tracker.sse_manager.broadcast_job_status_change(
            job_id=job_id,
            status="started"
        )

        yield tracker

    except Exception as e:
        # Send job failed event
        await tracker.fail(str(e))
        raise

    finally:
        # Ensure job is marked as finished if not already
        if tracker.progress < 100.0:
            await tracker.finish()


# Utility functions for common SSE operations
async def send_job_update(job_id: str, data: Dict[str, Any], event_type: str = "job_update"):
    """Send a custom job update via SSE."""
    sse_manager = get_sse_manager()
    event = SSEEvent(data=data, event=event_type, id=f"{job_id}-{event_type}")
    await sse_manager.broadcast_event(job_id, event)


async def send_job_message(job_id: str, message: str, level: str = "info"):
    """Send a job message via SSE."""
    data = {
        "job_id": job_id,
        "message": message,
        "level": level,
        "timestamp": datetime.now().isoformat()
    }
    await send_job_update(job_id, data, "job_message")


def format_sse_response(data: Dict[str, Any], event: str = "message") -> str:
    """Format data as SSE response string."""
    event_obj = SSEEvent(data=data, event=event)
    return event_obj.format()


# Connection monitoring
class SSEConnectionMonitor:
    """Monitors SSE connections and provides statistics."""

    def __init__(self):
        self.connection_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "connections_by_job": {},
            "average_connection_duration": 0.0
        }

    def track_connection_start(self, job_id: str):
        """Track when a connection starts."""
        self.connection_stats["total_connections"] += 1
        self.connection_stats["active_connections"] += 1

        if job_id not in self.connection_stats["connections_by_job"]:
            self.connection_stats["connections_by_job"][job_id] = 0
        self.connection_stats["connections_by_job"][job_id] += 1

    def track_connection_end(self, job_id: str, duration: float):
        """Track when a connection ends."""
        self.connection_stats["active_connections"] -= 1

        # Update average duration (simple moving average)
        current_avg = self.connection_stats["average_connection_duration"]
        total_conns = self.connection_stats["total_connections"]
        self.connection_stats["average_connection_duration"] = (
            (current_avg * (total_conns - 1) + duration) / total_conns
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return self.connection_stats.copy()


# Global connection monitor
_connection_monitor = SSEConnectionMonitor()