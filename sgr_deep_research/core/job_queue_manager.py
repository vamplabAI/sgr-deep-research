"""Job queue management for SGR Deep Research system.

This module provides the core job queue implementation for managing
long-running research jobs with prioritization and concurrency control.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from enum import Enum

import aiofiles

logger = logging.getLogger(__name__)


class JobState(str, Enum):
    """Job execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobPriority:
    """Job priority levels for queue ordering."""
    LOW = -10
    NORMAL = 0
    HIGH = 10
    URGENT = 20


class JobQueueItem:
    """Represents a job in the queue with priority and metadata."""

    def __init__(
        self,
        job_id: str,
        query: str,
        agent_type: str,
        deep_level: int = 0,
        priority: int = 0,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.job_id = job_id
        self.query = query
        self.agent_type = agent_type
        self.deep_level = deep_level
        self.priority = priority
        self.tags = tags or []
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.state = JobState.PENDING
        self.progress = 0.0
        self.current_step = ""
        self.steps_completed = 0
        self.total_steps = self._calculate_total_steps()
        self.searches_used = 0
        self.sources_found = 0
        self.error: Optional[Dict[str, Any]] = None
        self.result: Optional[Dict[str, Any]] = None

    def _calculate_total_steps(self) -> int:
        """Calculate estimated total steps based on deep level."""
        base_steps = 5
        return base_steps * (self.deep_level * 3 + 1)

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for JSON serialization."""
        return {
            "job_id": self.job_id,
            "query": self.query,
            "agent_type": self.agent_type,
            "deep_level": self.deep_level,
            "priority": self.priority,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "state": self.state.value,
            "progress": self.progress,
            "current_step": self.current_step,
            "steps_completed": self.steps_completed,
            "total_steps": self.total_steps,
            "searches_used": self.searches_used,
            "sources_found": self.sources_found,
            "error": self.error,
            "result": self.result
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobQueueItem":
        """Create job from dictionary (for deserialization)."""
        job = cls(
            job_id=data["job_id"],
            query=data["query"],
            agent_type=data["agent_type"],
            deep_level=data["deep_level"],
            priority=data["priority"],
            tags=data["tags"],
            metadata=data["metadata"]
        )

        # Restore state
        if data.get("created_at"):
            job.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("started_at"):
            job.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            job.completed_at = datetime.fromisoformat(data["completed_at"])

        job.state = JobState(data["state"])
        job.progress = data["progress"]
        job.current_step = data["current_step"]
        job.steps_completed = data["steps_completed"]
        job.total_steps = data["total_steps"]
        job.searches_used = data["searches_used"]
        job.sources_found = data["sources_found"]
        job.error = data.get("error")
        job.result = data.get("result")

        return job

    def __lt__(self, other: "JobQueueItem") -> bool:
        """Define ordering for priority queue (higher priority first)."""
        if self.priority != other.priority:
            return self.priority > other.priority  # Higher priority comes first
        return self.created_at < other.created_at  # FIFO for same priority


class JobQueue:
    """Main job queue implementation with persistence and concurrency control."""

    def __init__(
        self,
        max_concurrent_jobs: int = 3,
        persistence_dir: Optional[str] = None,
        cleanup_completed_after: timedelta = timedelta(hours=24)
    ):
        self.max_concurrent_jobs = max_concurrent_jobs
        self.cleanup_completed_after = cleanup_completed_after

        # Storage
        self.persistence_dir = Path(persistence_dir) if persistence_dir else Path("jobs")
        self.persistence_dir.mkdir(exist_ok=True)

        # Queue state
        self._pending_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running_jobs: Dict[str, JobQueueItem] = {}
        self._completed_jobs: Dict[str, JobQueueItem] = {}
        self._all_jobs: Dict[str, JobQueueItem] = {}

        # Concurrency control
        self._queue_lock = asyncio.Lock()
        self._worker_semaphore = asyncio.Semaphore(max_concurrent_jobs)

        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._persistence_task: Optional[asyncio.Task] = None

        # Event callbacks
        self._job_state_callbacks: List[callable] = []

    async def start(self):
        """Start the job queue and background tasks."""
        logger.info("Starting job queue...")

        # Load persisted jobs
        await self._load_persisted_jobs()

        # Start background tasks
        self._cleanup_task = asyncio.create_task(self._cleanup_worker())
        self._persistence_task = asyncio.create_task(self._persistence_worker())

        logger.info(f"Job queue started with {len(self._all_jobs)} existing jobs")

    async def stop(self):
        """Stop the job queue and background tasks."""
        logger.info("Stopping job queue...")

        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._persistence_task:
            self._persistence_task.cancel()

        # Save current state
        await self._persist_jobs()

        logger.info("Job queue stopped")

    async def submit_job(
        self,
        query: str,
        agent_type: str,
        deep_level: int = 0,
        priority: int = 0,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Submit a new job to the queue."""
        job_id = str(uuid.uuid4())

        job = JobQueueItem(
            job_id=job_id,
            query=query,
            agent_type=agent_type,
            deep_level=deep_level,
            priority=priority,
            tags=tags,
            metadata=metadata
        )

        async with self._queue_lock:
            self._all_jobs[job_id] = job
            await self._pending_queue.put(job)

        logger.info(f"Job {job_id} submitted to queue (priority: {priority})")
        await self._notify_job_state_change(job, "submitted")

        return job_id

    async def get_job(self, job_id: str) -> Optional[JobQueueItem]:
        """Get job by ID."""
        return self._all_jobs.get(job_id)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job (pending or running)."""
        async with self._queue_lock:
            job = self._all_jobs.get(job_id)
            if not job:
                return False

            if job.state == JobState.PENDING:
                job.state = JobState.CANCELLED
                job.completed_at = datetime.now()
                self._completed_jobs[job_id] = job
                logger.info(f"Job {job_id} cancelled (was pending)")
                await self._notify_job_state_change(job, "cancelled")
                return True
            elif job.state == JobState.RUNNING:
                job.state = JobState.CANCELLED
                job.completed_at = datetime.now()
                if job_id in self._running_jobs:
                    del self._running_jobs[job_id]
                self._completed_jobs[job_id] = job
                logger.info(f"Job {job_id} cancelled (was running)")
                await self._notify_job_state_change(job, "cancelled")
                return True
            else:
                return False  # Can't cancel completed/failed jobs

    async def list_jobs(
        self,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """List jobs with optional filtering."""
        jobs = list(self._all_jobs.values())

        # Filter by status
        if status:
            jobs = [job for job in jobs if job.state.value == status]

        # Filter by tags
        if tags:
            jobs = [job for job in jobs if any(tag in job.tags for tag in tags)]

        # Sort by creation time (newest first)
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        # Pagination
        total = len(jobs)
        jobs = jobs[offset:offset + limit]

        return {
            "jobs": [job.to_dict() for job in jobs],
            "total": total,
            "limit": limit,
            "offset": offset
        }

    async def get_next_job(self) -> Optional[JobQueueItem]:
        """Get the next job from the queue (for workers)."""
        try:
            job = await asyncio.wait_for(self._pending_queue.get(), timeout=1.0)

            async with self._queue_lock:
                if job.state == JobState.CANCELLED:
                    # Skip cancelled jobs
                    return await self.get_next_job()

                job.state = JobState.RUNNING
                job.started_at = datetime.now()
                self._running_jobs[job.job_id] = job

            await self._notify_job_state_change(job, "started")
            return job

        except asyncio.TimeoutError:
            return None

    async def mark_job_completed(self, job_id: str, result: Dict[str, Any]):
        """Mark a job as completed with results."""
        async with self._queue_lock:
            job = self._running_jobs.get(job_id)
            if job:
                job.state = JobState.COMPLETED
                job.completed_at = datetime.now()
                job.progress = 100.0
                job.current_step = "Completed"
                job.result = result

                del self._running_jobs[job_id]
                self._completed_jobs[job_id] = job

                logger.info(f"Job {job_id} completed successfully")
                await self._notify_job_state_change(job, "completed")

    async def mark_job_failed(self, job_id: str, error: Dict[str, Any]):
        """Mark a job as failed with error details."""
        async with self._queue_lock:
            job = self._running_jobs.get(job_id)
            if job:
                job.state = JobState.FAILED
                job.completed_at = datetime.now()
                job.error = error

                del self._running_jobs[job_id]
                self._completed_jobs[job_id] = job

                logger.error(f"Job {job_id} failed: {error}")
                await self._notify_job_state_change(job, "failed")

    async def update_job_progress(
        self,
        job_id: str,
        progress: float,
        current_step: str = "",
        steps_completed: int = None,
        searches_used: int = None,
        sources_found: int = None
    ):
        """Update job progress and status."""
        job = self._running_jobs.get(job_id)
        if job:
            job.progress = min(100.0, max(0.0, progress))
            if current_step:
                job.current_step = current_step
            if steps_completed is not None:
                job.steps_completed = steps_completed
            if searches_used is not None:
                job.searches_used = searches_used
            if sources_found is not None:
                job.sources_found = sources_found

            await self._notify_job_state_change(job, "progress")

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get current queue statistics."""
        return {
            "pending_jobs": self._pending_queue.qsize(),
            "running_jobs": len(self._running_jobs),
            "completed_jobs": len(self._completed_jobs),
            "total_jobs": len(self._all_jobs),
            "max_concurrent": self.max_concurrent_jobs,
            "current_load": len(self._running_jobs) / self.max_concurrent_jobs
        }

    def add_job_state_callback(self, callback: callable):
        """Add a callback for job state changes."""
        self._job_state_callbacks.append(callback)

    async def _notify_job_state_change(self, job: JobQueueItem, event: str):
        """Notify all callbacks of job state changes."""
        for callback in self._job_state_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(job, event)
                else:
                    callback(job, event)
            except Exception as e:
                logger.error(f"Error in job state callback: {e}")

    async def _cleanup_worker(self):
        """Background worker to clean up old completed jobs."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour

                cutoff_time = datetime.now() - self.cleanup_completed_after
                to_remove = []

                for job_id, job in self._completed_jobs.items():
                    if job.completed_at and job.completed_at < cutoff_time:
                        to_remove.append(job_id)

                for job_id in to_remove:
                    del self._completed_jobs[job_id]
                    del self._all_jobs[job_id]
                    # Remove persisted file
                    job_file = self.persistence_dir / f"{job_id}.json"
                    if job_file.exists():
                        job_file.unlink()

                if to_remove:
                    logger.info(f"Cleaned up {len(to_remove)} old completed jobs")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup worker: {e}")

    async def _persistence_worker(self):
        """Background worker to persist job state."""
        while True:
            try:
                await asyncio.sleep(60)  # Persist every minute
                await self._persist_jobs()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in persistence worker: {e}")

    async def _persist_jobs(self):
        """Persist current job state to disk."""
        try:
            for job in self._all_jobs.values():
                job_file = self.persistence_dir / f"{job.job_id}.json"
                async with aiofiles.open(job_file, 'w') as f:
                    await f.write(json.dumps(job.to_dict(), indent=2))
        except Exception as e:
            logger.error(f"Error persisting jobs: {e}")

    async def _load_persisted_jobs(self):
        """Load persisted jobs from disk."""
        try:
            for job_file in self.persistence_dir.glob("*.json"):
                async with aiofiles.open(job_file, 'r') as f:
                    data = json.loads(await f.read())
                    job = JobQueueItem.from_dict(data)
                    self._all_jobs[job.job_id] = job

                    # Restore to appropriate collections
                    if job.state == JobState.PENDING:
                        await self._pending_queue.put(job)
                    elif job.state == JobState.RUNNING:
                        # Reset running jobs to pending on restart
                        job.state = JobState.PENDING
                        await self._pending_queue.put(job)
                    else:
                        self._completed_jobs[job.job_id] = job

        except Exception as e:
            logger.error(f"Error loading persisted jobs: {e}")


# Global job queue instance
_global_job_queue: Optional[JobQueue] = None


async def get_job_queue() -> JobQueue:
    """Get the global job queue instance."""
    global _global_job_queue
    if _global_job_queue is None:
        _global_job_queue = JobQueue()
        await _global_job_queue.start()
    return _global_job_queue


async def shutdown_job_queue():
    """Shutdown the global job queue."""
    global _global_job_queue
    if _global_job_queue:
        await _global_job_queue.stop()
        _global_job_queue = None