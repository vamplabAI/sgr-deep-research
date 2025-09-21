"""Job storage service for persistent job management.

This module provides the JobStorage service for persisting job data,
including job status, results, and error information.
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import uuid4
import aiofiles
from contextlib import asynccontextmanager

from ..api.models import (
    JobRequest, JobStatus, JobResult, JobError, JobState,
    ResearchSource, ExecutionMetrics
)


class JobStorageError(Exception):
    """Exception raised by job storage operations."""
    pass


class JobStorage:
    """Service for persistent job data storage.

    Provides file-based storage for job metadata, status, results, and errors
    with support for in-memory caching and eventual Redis migration.
    """

    def __init__(self, storage_dir: str = "jobs", cache_size: int = 1000):
        """Initialize job storage service.

        Args:
            storage_dir: Base directory for job storage
            cache_size: Maximum number of jobs to keep in memory cache
        """
        self.storage_dir = Path(storage_dir)
        self.cache_size = cache_size

        # Create storage directories
        self.jobs_dir = self.storage_dir / "jobs"
        self.results_dir = self.storage_dir / "results"
        self.errors_dir = self.storage_dir / "errors"
        self.reports_dir = self.storage_dir / "reports"

        for directory in [self.jobs_dir, self.results_dir, self.errors_dir, self.reports_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        # In-memory cache for fast access
        self._job_cache: Dict[str, JobStatus] = {}
        self._result_cache: Dict[str, JobResult] = {}
        self._error_cache: Dict[str, JobError] = {}

        # Cache ordering for LRU eviction
        self._cache_order: List[str] = []

        # File locks for concurrent access
        self._file_locks: Dict[str, asyncio.Lock] = {}
        self._lock_cleanup_interval = 300  # 5 minutes

        # Start background cleanup task
        self._cleanup_task = None
        self._start_cleanup_task()

    def _start_cleanup_task(self):
        """Start background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_old_locks())

    async def _cleanup_old_locks(self):
        """Clean up old file locks periodically."""
        while True:
            try:
                await asyncio.sleep(self._lock_cleanup_interval)

                # Remove unused locks
                current_locks = list(self._file_locks.keys())
                for lock_key in current_locks:
                    lock = self._file_locks.get(lock_key)
                    if lock and not lock.locked():
                        del self._file_locks[lock_key]

            except asyncio.CancelledError:
                break
            except Exception:
                # Continue cleanup on errors
                continue

    def _get_file_lock(self, file_path: str) -> asyncio.Lock:
        """Get or create a file lock for the given path."""
        if file_path not in self._file_locks:
            self._file_locks[file_path] = asyncio.Lock()
        return self._file_locks[file_path]

    def _get_job_file_path(self, job_id: str) -> Path:
        """Get file path for job metadata."""
        return self.jobs_dir / f"{job_id}.json"

    def _get_result_file_path(self, job_id: str) -> Path:
        """Get file path for job result."""
        return self.results_dir / f"{job_id}.json"

    def _get_error_file_path(self, job_id: str) -> Path:
        """Get file path for job error."""
        return self.errors_dir / f"{job_id}.json"

    def _get_report_file_path(self, job_id: str) -> Path:
        """Get file path for job report."""
        return self.reports_dir / f"{job_id}.md"

    def _update_cache_order(self, job_id: str):
        """Update cache ordering for LRU eviction."""
        if job_id in self._cache_order:
            self._cache_order.remove(job_id)
        self._cache_order.append(job_id)

        # Evict old entries if cache is full
        while len(self._cache_order) > self.cache_size:
            old_job_id = self._cache_order.pop(0)
            self._job_cache.pop(old_job_id, None)
            self._result_cache.pop(old_job_id, None)
            self._error_cache.pop(old_job_id, None)

    async def create_job(self, job_request: JobRequest) -> JobStatus:
        """Create a new job from request.

        Args:
            job_request: Job submission request

        Returns:
            JobStatus: Initial job status

        Raises:
            JobStorageError: If job creation fails
        """
        job_id = str(uuid4())

        # Create initial job status
        job_status = JobStatus(
            job_id=job_id,
            status=JobState.PENDING,
            progress=0.0,
            current_step="Job queued for processing",
            steps_completed=0,
            total_steps=job_request.get_effective_iterations(),
            created_at=datetime.utcnow(),
            query=job_request.query[:200],  # Truncated for display
            agent_type=job_request.agent_type,
            tags=job_request.tags,
            priority=job_request.priority
        )

        try:
            await self.save_job(job_status)
            return job_status
        except Exception as e:
            raise JobStorageError(f"Failed to create job {job_id}: {e}")

    async def save_job(self, job_status: JobStatus) -> None:
        """Save job status to storage.

        Args:
            job_status: Job status to save

        Raises:
            JobStorageError: If save operation fails
        """
        file_path = self._get_job_file_path(job_status.job_id)

        async with self._get_file_lock(str(file_path)):
            try:
                # Update last_updated timestamp
                job_status.last_updated = datetime.utcnow()

                # Save to file
                async with aiofiles.open(file_path, 'w') as f:
                    await f.write(job_status.json(indent=2))

                # Update cache
                self._job_cache[job_status.job_id] = job_status
                self._update_cache_order(job_status.job_id)

            except Exception as e:
                raise JobStorageError(f"Failed to save job {job_status.job_id}: {e}")

    async def get_job(self, job_id: str) -> Optional[JobStatus]:
        """Get job status by ID.

        Args:
            job_id: Job identifier

        Returns:
            JobStatus or None if not found

        Raises:
            JobStorageError: If retrieval fails
        """
        # Check cache first
        if job_id in self._job_cache:
            self._update_cache_order(job_id)
            return self._job_cache[job_id]

        # Load from file
        file_path = self._get_job_file_path(job_id)

        if not file_path.exists():
            return None

        async with self._get_file_lock(str(file_path)):
            try:
                async with aiofiles.open(file_path, 'r') as f:
                    content = await f.read()

                job_status = JobStatus.parse_raw(content)

                # Update cache
                self._job_cache[job_id] = job_status
                self._update_cache_order(job_id)

                return job_status

            except Exception as e:
                raise JobStorageError(f"Failed to load job {job_id}: {e}")

    async def update_job_progress(self, job_id: str,
                                progress: float,
                                current_step: str = None,
                                steps_completed: int = None) -> None:
        """Update job progress information.

        Args:
            job_id: Job identifier
            progress: Progress percentage (0.0-100.0)
            current_step: Current step description
            steps_completed: Number of completed steps

        Raises:
            JobStorageError: If update fails
        """
        job_status = await self.get_job(job_id)
        if not job_status:
            raise JobStorageError(f"Job {job_id} not found")

        # Update progress fields
        job_status.progress = progress
        if current_step is not None:
            job_status.current_step = current_step
        if steps_completed is not None:
            job_status.steps_completed = steps_completed

        # Update status based on progress
        if progress >= 100.0 and job_status.status == JobState.RUNNING:
            job_status.status = JobState.COMPLETED
            job_status.completed_at = datetime.utcnow()

        await self.save_job(job_status)

    async def start_job(self, job_id: str) -> None:
        """Mark job as started.

        Args:
            job_id: Job identifier

        Raises:
            JobStorageError: If job not found or update fails
        """
        job_status = await self.get_job(job_id)
        if not job_status:
            raise JobStorageError(f"Job {job_id} not found")

        if job_status.status != JobState.PENDING:
            raise JobStorageError(f"Job {job_id} is not in pending state")

        job_status.status = JobState.RUNNING
        job_status.started_at = datetime.utcnow()
        job_status.current_step = "Starting job execution"

        await self.save_job(job_status)

    async def complete_job(self, job_id: str) -> None:
        """Mark job as completed.

        Args:
            job_id: Job identifier

        Raises:
            JobStorageError: If job not found or update fails
        """
        job_status = await self.get_job(job_id)
        if not job_status:
            raise JobStorageError(f"Job {job_id} not found")

        job_status.status = JobState.COMPLETED
        job_status.progress = 100.0
        job_status.completed_at = datetime.utcnow()
        job_status.current_step = "Job completed successfully"

        # Calculate runtime
        if job_status.started_at:
            runtime = job_status.completed_at - job_status.started_at
            job_status.runtime_seconds = runtime.total_seconds()

        await self.save_job(job_status)

    async def fail_job(self, job_id: str, error: JobError) -> None:
        """Mark job as failed and save error.

        Args:
            job_id: Job identifier
            error: Error information

        Raises:
            JobStorageError: If job not found or update fails
        """
        job_status = await self.get_job(job_id)
        if not job_status:
            raise JobStorageError(f"Job {job_id} not found")

        job_status.status = JobState.FAILED
        job_status.completed_at = datetime.utcnow()
        job_status.current_step = f"Job failed: {error.error_message}"

        # Calculate runtime
        if job_status.started_at:
            runtime = job_status.completed_at - job_status.started_at
            job_status.runtime_seconds = runtime.total_seconds()

        await self.save_job(job_status)
        await self.save_error(error)

    async def cancel_job(self, job_id: str, reason: str = "User requested cancellation") -> None:
        """Cancel a job.

        Args:
            job_id: Job identifier
            reason: Cancellation reason

        Raises:
            JobStorageError: If job not found or cannot be cancelled
        """
        job_status = await self.get_job(job_id)
        if not job_status:
            raise JobStorageError(f"Job {job_id} not found")

        if not job_status.can_be_cancelled():
            raise JobStorageError(f"Job {job_id} cannot be cancelled (status: {job_status.status})")

        job_status.status = JobState.CANCELLED
        job_status.completed_at = datetime.utcnow()
        job_status.current_step = f"Job cancelled: {reason}"

        # Calculate runtime if started
        if job_status.started_at:
            runtime = job_status.completed_at - job_status.started_at
            job_status.runtime_seconds = runtime.total_seconds()

        await self.save_job(job_status)

    async def save_result(self, result: JobResult) -> None:
        """Save job result to storage.

        Args:
            result: Job result to save

        Raises:
            JobStorageError: If save operation fails
        """
        file_path = self._get_result_file_path(result.job_id)

        async with self._get_file_lock(str(file_path)):
            try:
                # Save result to JSON file
                async with aiofiles.open(file_path, 'w') as f:
                    await f.write(result.json(indent=2))

                # Save report to markdown file if available
                if result.final_answer:
                    report_path = self._get_report_file_path(result.job_id)
                    async with aiofiles.open(report_path, 'w') as f:
                        await f.write(result.final_answer)

                # Update cache
                self._result_cache[result.job_id] = result
                self._update_cache_order(result.job_id)

            except Exception as e:
                raise JobStorageError(f"Failed to save result for job {result.job_id}: {e}")

    async def get_result(self, job_id: str) -> Optional[JobResult]:
        """Get job result by ID.

        Args:
            job_id: Job identifier

        Returns:
            JobResult or None if not found

        Raises:
            JobStorageError: If retrieval fails
        """
        # Check cache first
        if job_id in self._result_cache:
            self._update_cache_order(job_id)
            return self._result_cache[job_id]

        # Load from file
        file_path = self._get_result_file_path(job_id)

        if not file_path.exists():
            return None

        async with self._get_file_lock(str(file_path)):
            try:
                async with aiofiles.open(file_path, 'r') as f:
                    content = await f.read()

                result = JobResult.parse_raw(content)

                # Update cache
                self._result_cache[job_id] = result
                self._update_cache_order(job_id)

                return result

            except Exception as e:
                raise JobStorageError(f"Failed to load result for job {job_id}: {e}")

    async def save_error(self, error: JobError) -> None:
        """Save job error to storage.

        Args:
            error: Job error to save

        Raises:
            JobStorageError: If save operation fails
        """
        file_path = self._get_error_file_path(error.job_id)

        async with self._get_file_lock(str(file_path)):
            try:
                async with aiofiles.open(file_path, 'w') as f:
                    await f.write(error.json(indent=2))

                # Update cache
                self._error_cache[error.job_id] = error
                self._update_cache_order(error.job_id)

            except Exception as e:
                raise JobStorageError(f"Failed to save error for job {error.job_id}: {e}")

    async def get_error(self, job_id: str) -> Optional[JobError]:
        """Get job error by ID.

        Args:
            job_id: Job identifier

        Returns:
            JobError or None if not found

        Raises:
            JobStorageError: If retrieval fails
        """
        # Check cache first
        if job_id in self._error_cache:
            self._update_cache_order(job_id)
            return self._error_cache[job_id]

        # Load from file
        file_path = self._get_error_file_path(job_id)

        if not file_path.exists():
            return None

        async with self._get_file_lock(str(file_path)):
            try:
                async with aiofiles.open(file_path, 'r') as f:
                    content = await f.read()

                error = JobError.parse_raw(content)

                # Update cache
                self._error_cache[job_id] = error
                self._update_cache_order(job_id)

                return error

            except Exception as e:
                raise JobStorageError(f"Failed to load error for job {job_id}: {e}")

    async def list_jobs(self,
                       limit: int = 50,
                       offset: int = 0,
                       status_filter: Optional[JobState] = None,
                       tags_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        """List jobs with filtering and pagination.

        Args:
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip
            status_filter: Filter by job status
            tags_filter: Filter by tags (any match)

        Returns:
            Dict with jobs list, total count, limit, and offset

        Raises:
            JobStorageError: If listing fails
        """
        try:
            # Get all job files
            job_files = list(self.jobs_dir.glob("*.json"))

            # Load job summaries
            jobs = []
            for job_file in job_files:
                try:
                    async with aiofiles.open(job_file, 'r') as f:
                        content = await f.read()

                    job_status = JobStatus.parse_raw(content)

                    # Apply filters
                    if status_filter and job_status.status != status_filter:
                        continue

                    if tags_filter and job_status.tags:
                        if not any(tag in job_status.tags for tag in tags_filter):
                            continue

                    jobs.append(job_status)

                except Exception:
                    # Skip corrupted files
                    continue

            # Sort by created_at descending (newest first)
            jobs.sort(key=lambda j: j.created_at, reverse=True)

            # Apply pagination
            total = len(jobs)
            paginated_jobs = jobs[offset:offset + limit]

            # Convert to dict format for API response
            job_dicts = []
            for job in paginated_jobs:
                job_dict = job.dict()

                # Include summary fields only for list view
                summary_dict = {
                    "job_id": job_dict["job_id"],
                    "status": job_dict["status"],
                    "progress": job_dict["progress"],
                    "current_step": job_dict["current_step"],
                    "created_at": job_dict["created_at"],
                    "query": job_dict.get("query", ""),
                    "agent_type": job_dict.get("agent_type"),
                    "tags": job_dict.get("tags", []),
                    "priority": job_dict.get("priority", 0)
                }

                # Add completion time for finished jobs
                if job.completed_at:
                    summary_dict["completed_at"] = job_dict["completed_at"]

                # Add runtime for completed jobs
                if job.runtime_seconds:
                    summary_dict["runtime_seconds"] = job_dict["runtime_seconds"]

                job_dicts.append(summary_dict)

            return {
                "jobs": job_dicts,
                "total": total,
                "limit": limit,
                "offset": offset
            }

        except Exception as e:
            raise JobStorageError(f"Failed to list jobs: {e}")

    async def delete_job(self, job_id: str) -> bool:
        """Delete job and all associated data.

        Args:
            job_id: Job identifier

        Returns:
            bool: True if job was deleted, False if not found

        Raises:
            JobStorageError: If deletion fails
        """
        job_exists = False

        try:
            # Delete all related files
            files_to_delete = [
                self._get_job_file_path(job_id),
                self._get_result_file_path(job_id),
                self._get_error_file_path(job_id),
                self._get_report_file_path(job_id)
            ]

            for file_path in files_to_delete:
                if file_path.exists():
                    job_exists = True
                    await asyncio.to_thread(file_path.unlink)

            # Remove from cache
            self._job_cache.pop(job_id, None)
            self._result_cache.pop(job_id, None)
            self._error_cache.pop(job_id, None)

            if job_id in self._cache_order:
                self._cache_order.remove(job_id)

            return job_exists

        except Exception as e:
            raise JobStorageError(f"Failed to delete job {job_id}: {e}")

    async def cleanup_old_jobs(self, max_age_days: int = 30) -> int:
        """Clean up old completed jobs.

        Args:
            max_age_days: Maximum age in days for keeping jobs

        Returns:
            int: Number of jobs cleaned up

        Raises:
            JobStorageError: If cleanup fails
        """
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        cleaned_count = 0

        try:
            # Get all job files
            job_files = list(self.jobs_dir.glob("*.json"))

            for job_file in job_files:
                try:
                    async with aiofiles.open(job_file, 'r') as f:
                        content = await f.read()

                    job_status = JobStatus.parse_raw(content)

                    # Only clean up completed/failed/cancelled jobs
                    if (job_status.is_terminal_state() and
                        job_status.completed_at and
                        job_status.completed_at < cutoff_date):

                        await self.delete_job(job_status.job_id)
                        cleaned_count += 1

                except Exception:
                    # Skip corrupted files
                    continue

            return cleaned_count

        except Exception as e:
            raise JobStorageError(f"Failed to cleanup old jobs: {e}")

    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics.

        Returns:
            Dict with storage statistics

        Raises:
            JobStorageError: If stat collection fails
        """
        try:
            stats = {
                "total_jobs": 0,
                "jobs_by_status": {},
                "cache_size": len(self._job_cache),
                "storage_size_mb": 0.0
            }

            # Count files and calculate sizes
            for directory, label in [
                (self.jobs_dir, "jobs"),
                (self.results_dir, "results"),
                (self.errors_dir, "errors"),
                (self.reports_dir, "reports")
            ]:
                if directory.exists():
                    files = list(directory.glob("*"))
                    if label == "jobs":
                        stats["total_jobs"] = len(files)

                    # Calculate directory size
                    for file_path in files:
                        if file_path.is_file():
                            stats["storage_size_mb"] += file_path.stat().st_size

            # Convert bytes to MB
            stats["storage_size_mb"] = round(stats["storage_size_mb"] / (1024 * 1024), 2)

            # Count by status (from cache and recent files)
            status_counts = {}
            for job_status in self._job_cache.values():
                status = job_status.status
                status_counts[status] = status_counts.get(status, 0) + 1

            stats["jobs_by_status"] = status_counts

            return stats

        except Exception as e:
            raise JobStorageError(f"Failed to get storage stats: {e}")

    async def close(self):
        """Close storage and cleanup resources."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Clear caches
        self._job_cache.clear()
        self._result_cache.clear()
        self._error_cache.clear()
        self._cache_order.clear()
        self._file_locks.clear()


# Global storage instance
_storage_instance: Optional[JobStorage] = None


def get_job_storage() -> JobStorage:
    """Get the global job storage instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = JobStorage()
    return _storage_instance


async def close_job_storage():
    """Close the global job storage instance."""
    global _storage_instance
    if _storage_instance:
        await _storage_instance.close()
        _storage_instance = None