"""Job queue management service for coordinating job execution.

This module provides the JobQueueManager service that coordinates between
job submission, queueing, and execution using the existing job queue and executor.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from ..api.models import (
    JobRequest, JobStatus, JobState, ErrorType, ErrorSeverity
)
from .job_storage import get_job_storage
from .job_executor import get_job_executor
from .job_queue import get_job_queue

logger = logging.getLogger(__name__)


class JobQueueManagerError(Exception):
    """Exception raised by job queue manager operations."""
    pass


class JobQueueManager:
    """Service for managing job queue and execution coordination.

    Coordinates between job submission, priority queueing, and execution
    while managing system resources and concurrency limits.
    """

    def __init__(self,
                 max_queue_size: int = 1000,
                 max_concurrent_jobs: int = 5,
                 queue_check_interval: float = 1.0):
        """Initialize job queue manager.

        Args:
            max_queue_size: Maximum number of jobs in queue
            max_concurrent_jobs: Maximum concurrent executing jobs
            max_concurrent_jobs: Maximum concurrent executing jobs
            queue_check_interval: Interval between queue processing checks
        """
        self.max_queue_size = max_queue_size
        self.max_concurrent_jobs = max_concurrent_jobs
        self.queue_check_interval = queue_check_interval

        # Service dependencies
        self.storage = get_job_storage()
        self.executor = get_job_executor()
        self.queue = get_job_queue()

        # Queue processing task
        self._queue_processor_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        # Statistics
        self._stats = {
            "jobs_submitted": 0,
            "jobs_queued": 0,
            "jobs_executed": 0,
            "jobs_rejected": 0,
            "queue_full_events": 0,
            "total_queue_time": 0.0
        }

        # Job submission timestamps for queue time tracking
        self._submission_times: Dict[str, datetime] = {}

    async def start(self):
        """Start the queue manager and processing loop."""
        if self._queue_processor_task is None or self._queue_processor_task.done():
            logger.info("Starting job queue manager")
            self._queue_processor_task = asyncio.create_task(
                self._queue_processor_loop(),
                name="job-queue-processor"
            )

    async def stop(self):
        """Stop the queue manager and processing loop."""
        logger.info("Stopping job queue manager")
        self._shutdown_event.set()

        if self._queue_processor_task:
            self._queue_processor_task.cancel()
            try:
                await self._queue_processor_task
            except asyncio.CancelledError:
                pass

        self._queue_processor_task = None

    @asynccontextmanager
    async def managed_lifecycle(self):
        """Context manager for automatic start/stop lifecycle."""
        await self.start()
        try:
            yield self
        finally:
            await self.stop()

    async def submit_job(self, job_request: JobRequest) -> str:
        """Submit a job for execution.

        Args:
            job_request: Job submission request

        Returns:
            str: Job ID

        Raises:
            JobQueueManagerError: If submission fails
        """
        try:
            # Check queue capacity
            if await self.queue.size() >= self.max_queue_size:
                self._stats["queue_full_events"] += 1
                raise JobQueueManagerError(
                    f"Queue is full (max size: {self.max_queue_size}). Please try again later."
                )

            # Create job in storage
            job_status = await self.storage.create_job(job_request)
            job_id = job_status.job_id

            logger.info(f"Submitting job {job_id} to queue: {job_request.query[:100]}")

            # Add to queue
            await self.queue.submit_job(job_request, job_id)

            # Track submission time
            self._submission_times[job_id] = datetime.utcnow()

            # Update statistics
            self._stats["jobs_submitted"] += 1
            self._stats["jobs_queued"] += 1

            logger.info(f"Job {job_id} queued successfully with priority {job_request.priority}")

            return job_id

        except Exception as e:
            self._stats["jobs_rejected"] += 1
            if isinstance(e, JobQueueManagerError):
                raise
            raise JobQueueManagerError(f"Failed to submit job: {e}")

    async def cancel_job(self, job_id: str, reason: str = "User requested cancellation") -> bool:
        """Cancel a job (queued or running).

        Args:
            job_id: Job identifier
            reason: Cancellation reason

        Returns:
            bool: True if job was cancelled

        Raises:
            JobQueueManagerError: If cancellation fails
        """
        try:
            logger.info(f"Cancelling job {job_id}: {reason}")

            # Try to remove from queue first
            removed_from_queue = await self.queue.cancel_job(job_id)

            if removed_from_queue:
                # Job was in queue, cancel in storage
                await self.storage.cancel_job(job_id, reason)
                self._cleanup_job_tracking(job_id)
                logger.info(f"Job {job_id} removed from queue")
                return True

            # Try to cancel running job
            cancelled_running = await self.executor.cancel_job(job_id, reason)

            if cancelled_running:
                self._cleanup_job_tracking(job_id)
                logger.info(f"Running job {job_id} cancelled")
                return True

            # Job might be in storage only (not found in queue or executor)
            try:
                await self.storage.cancel_job(job_id, reason)
                self._cleanup_job_tracking(job_id)
                return True
            except Exception:
                return False

        except Exception as e:
            raise JobQueueManagerError(f"Failed to cancel job {job_id}: {e}")

    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status and statistics.

        Returns:
            Dict: Queue status information
        """
        try:
            queue_size = await self.queue.size()
            running_jobs = await self.executor.get_running_jobs()
            executor_stats = await self.executor.get_execution_stats()

            return {
                "queue_size": queue_size,
                "max_queue_size": self.max_queue_size,
                "running_jobs": len(running_jobs),
                "max_concurrent_jobs": self.max_concurrent_jobs,
                "capacity_available": self.max_queue_size - queue_size,
                "execution_slots_available": self.max_concurrent_jobs - len(running_jobs),
                "queue_utilization": (queue_size / self.max_queue_size) * 100,
                "execution_utilization": (len(running_jobs) / self.max_concurrent_jobs) * 100,
                "statistics": self._stats.copy(),
                "executor_statistics": executor_stats
            }

        except Exception as e:
            raise JobQueueManagerError(f"Failed to get queue status: {e}")

    async def get_job_position(self, job_id: str) -> Optional[int]:
        """Get job position in queue.

        Args:
            job_id: Job identifier

        Returns:
            Optional[int]: Position in queue (1-based) or None if not in queue
        """
        try:
            return await self.queue.get_job_position(job_id)
        except Exception as e:
            logger.warning(f"Failed to get job position for {job_id}: {e}")
            return None

    async def get_estimated_wait_time(self, job_id: str) -> Optional[timedelta]:
        """Get estimated wait time for a job in queue.

        Args:
            job_id: Job identifier

        Returns:
            Optional[timedelta]: Estimated wait time or None if not calculable
        """
        try:
            position = await self.get_job_position(job_id)
            if position is None:
                return None

            # Simple estimation based on average job execution time
            executor_stats = await self.executor.get_execution_stats()

            total_jobs = executor_stats.get("jobs_completed", 0)
            total_time = executor_stats.get("total_execution_time", 0)

            if total_jobs > 0:
                avg_job_time = total_time / total_jobs
            else:
                avg_job_time = 300  # Default 5 minutes

            # Estimate wait time based on position and concurrent capacity
            jobs_ahead = max(0, position - 1)
            concurrent_slots = self.max_concurrent_jobs

            estimated_seconds = (jobs_ahead / concurrent_slots) * avg_job_time
            return timedelta(seconds=estimated_seconds)

        except Exception as e:
            logger.warning(f"Failed to estimate wait time for job {job_id}: {e}")
            return None

    async def adjust_job_priority(self, job_id: str, new_priority: int) -> bool:
        """Adjust priority of a queued job.

        Args:
            job_id: Job identifier
            new_priority: New priority value

        Returns:
            bool: True if priority was adjusted

        Raises:
            JobQueueManagerError: If adjustment fails
        """
        try:
            # Check if job is in queue
            position = await self.get_job_position(job_id)
            if position is None:
                return False

            # Update priority in queue
            success = await self.queue.adjust_priority(job_id, new_priority)

            if success:
                logger.info(f"Adjusted priority for job {job_id} to {new_priority}")

            return success

        except Exception as e:
            raise JobQueueManagerError(f"Failed to adjust priority for job {job_id}: {e}")

    async def pause_queue_processing(self):
        """Pause queue processing temporarily."""
        logger.info("Pausing queue processing")
        # Implementation would set a pause flag
        # For now, this is a placeholder
        pass

    async def resume_queue_processing(self):
        """Resume queue processing."""
        logger.info("Resuming queue processing")
        # Implementation would clear pause flag
        # For now, this is a placeholder
        pass

    async def _queue_processor_loop(self):
        """Main queue processing loop."""
        logger.info("Starting queue processor loop")

        while not self._shutdown_event.is_set():
            try:
                await self._process_queue_batch()
                await asyncio.sleep(self.queue_check_interval)

            except asyncio.CancelledError:
                logger.info("Queue processor loop cancelled")
                break

            except Exception as e:
                logger.error(f"Error in queue processor loop: {e}", exc_info=True)
                await asyncio.sleep(self.queue_check_interval * 2)  # Back off on error

        logger.info("Queue processor loop stopped")

    async def _process_queue_batch(self):
        """Process a batch of jobs from the queue."""
        try:
            # Check if we can start more jobs
            running_jobs = await self.executor.get_running_jobs()
            available_slots = self.max_concurrent_jobs - len(running_jobs)

            if available_slots <= 0:
                return

            # Get jobs to process
            jobs_to_process = min(available_slots, 5)  # Process up to 5 jobs at once

            for _ in range(jobs_to_process):
                # Get next job from queue
                job_data = await self.queue.get_next_job()

                if job_data is None:
                    break  # Queue is empty

                job_request, job_id = job_data

                try:
                    # Check if executor can start the job
                    if not await self.executor.can_start_job():
                        # Put job back in queue if can't start
                        await self.queue.submit_job(job_request, job_id)
                        break

                    # Start job execution
                    logger.info(f"Starting execution for job {job_id}")

                    # Calculate queue time
                    if job_id in self._submission_times:
                        queue_time = (datetime.utcnow() - self._submission_times[job_id]).total_seconds()
                        self._stats["total_queue_time"] += queue_time

                    # Start the job
                    await self.executor.start_job(job_request)

                    # Update statistics
                    self._stats["jobs_executed"] += 1

                    # Cleanup tracking
                    self._cleanup_job_tracking(job_id)

                except Exception as e:
                    logger.error(f"Failed to start job {job_id}: {e}")

                    # Handle job start failure
                    await self._handle_job_start_failure(job_id, job_request, e)

        except Exception as e:
            logger.error(f"Error processing queue batch: {e}")

    async def _handle_job_start_failure(self, job_id: str, job_request: JobRequest, error: Exception):
        """Handle failure to start job execution.

        Args:
            job_id: Job identifier
            job_request: Original job request
            error: Exception that occurred
        """
        try:
            # Create error record
            from ..api.models import JobError

            job_error = JobError(
                job_id=job_id,
                error_type=ErrorType.SYSTEM_ERROR,
                error_message=f"Failed to start job execution: {str(error)}",
                severity=ErrorSeverity.HIGH,
                occurred_at=datetime.utcnow(),
                is_retryable=True
            )

            # Determine if we should retry
            if job_error.should_retry_automatically():
                logger.info(f"Retrying job {job_id} after start failure")

                # Put back in queue with slight delay
                await asyncio.sleep(1.0)
                await self.queue.submit_job(job_request, job_id)

                job_error.retry_count += 1
                await self.storage.save_error(job_error)
            else:
                logger.error(f"Job {job_id} failed to start and cannot be retried")
                await self.storage.fail_job(job_id, job_error)
                self._cleanup_job_tracking(job_id)

        except Exception as e:
            logger.error(f"Failed to handle job start failure for {job_id}: {e}")

    def _cleanup_job_tracking(self, job_id: str):
        """Clean up job tracking data.

        Args:
            job_id: Job identifier
        """
        self._submission_times.pop(job_id, None)

    async def cleanup_old_tracking_data(self, max_age_hours: int = 24):
        """Clean up old job tracking data.

        Args:
            max_age_hours: Maximum age in hours for keeping tracking data
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

        old_jobs = [
            job_id for job_id, submit_time in self._submission_times.items()
            if submit_time < cutoff_time
        ]

        for job_id in old_jobs:
            self._cleanup_job_tracking(job_id)

        if old_jobs:
            logger.info(f"Cleaned up tracking data for {len(old_jobs)} old jobs")

    async def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the entire job management system.

        Returns:
            Dict: Comprehensive status information
        """
        try:
            queue_status = await self.get_queue_status()
            storage_stats = await self.storage.get_storage_stats()

            # Get sample of recent jobs
            recent_jobs = await self.storage.list_jobs(limit=10, offset=0)

            status = {
                "queue_manager": {
                    "status": "running" if self._queue_processor_task and not self._queue_processor_task.done() else "stopped",
                    "queue_check_interval": self.queue_check_interval,
                    "tracked_submissions": len(self._submission_times)
                },
                "queue_status": queue_status,
                "storage_status": storage_stats,
                "recent_jobs": recent_jobs["jobs"][:5],  # Last 5 jobs
                "system_health": {
                    "queue_utilization": queue_status["queue_utilization"],
                    "execution_utilization": queue_status["execution_utilization"],
                    "error_rate": self._calculate_error_rate(),
                    "avg_queue_time": self._calculate_avg_queue_time()
                }
            }

            return status

        except Exception as e:
            raise JobQueueManagerError(f"Failed to get comprehensive status: {e}")

    def _calculate_error_rate(self) -> float:
        """Calculate error rate percentage."""
        total_jobs = self._stats["jobs_submitted"]
        if total_jobs == 0:
            return 0.0

        failed_jobs = self._stats["jobs_rejected"]
        return (failed_jobs / total_jobs) * 100

    def _calculate_avg_queue_time(self) -> float:
        """Calculate average queue time in seconds."""
        executed_jobs = self._stats["jobs_executed"]
        if executed_jobs == 0:
            return 0.0

        return self._stats["total_queue_time"] / executed_jobs

    async def close(self):
        """Close queue manager and cleanup resources."""
        await self.stop()

        # Cleanup tracking data
        self._submission_times.clear()


# Global queue manager instance
_queue_manager_instance: Optional[JobQueueManager] = None


def get_job_queue_manager() -> JobQueueManager:
    """Get the global job queue manager instance."""
    global _queue_manager_instance
    if _queue_manager_instance is None:
        _queue_manager_instance = JobQueueManager()
    return _queue_manager_instance


async def close_job_queue_manager():
    """Close the global job queue manager instance."""
    global _queue_manager_instance
    if _queue_manager_instance:
        await _queue_manager_instance.close()
        _queue_manager_instance = None