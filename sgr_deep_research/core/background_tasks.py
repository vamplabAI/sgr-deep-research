"""Background task runner for job execution.

This module provides background task management for long-running research jobs,
including task scheduling, monitoring, and lifecycle management.
"""

import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

from sgr_deep_research.core.job_storage import JobStorage
from sgr_deep_research.core.job_queue_manager import JobQueueManager
from sgr_deep_research.core.job_executor import JobExecutor
from sgr_deep_research.api.models import JobState

logger = logging.getLogger(__name__)


class BackgroundTaskRunner:
    """Manages background execution of research jobs."""

    def __init__(
        self,
        job_storage: JobStorage,
        job_queue_manager: JobQueueManager,
        job_executor: JobExecutor,
        max_concurrent_jobs: int = 3,
        cleanup_interval: int = 300  # 5 minutes
    ):
        self.job_storage = job_storage
        self.job_queue_manager = job_queue_manager
        self.job_executor = job_executor
        self.max_concurrent_jobs = max_concurrent_jobs
        self.cleanup_interval = cleanup_interval

        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.is_running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the background task runner."""
        if self.is_running:
            logger.warning("Background task runner is already running")
            return

        self.is_running = True
        logger.info("Starting background task runner")

        # Start monitoring and cleanup tasks
        self._monitor_task = asyncio.create_task(self._monitor_jobs())
        self._cleanup_task = asyncio.create_task(self._cleanup_completed_jobs())

    async def stop(self) -> None:
        """Stop the background task runner and cancel running tasks."""
        if not self.is_running:
            return

        logger.info("Stopping background task runner")
        self.is_running = False

        # Cancel monitor and cleanup tasks
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Cancel all running job tasks
        for job_id, task in self.running_tasks.items():
            logger.info(f"Cancelling job task {job_id}")
            task.cancel()

        # Wait for all tasks to complete
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks.values(), return_exceptions=True)

        self.running_tasks.clear()
        logger.info("Background task runner stopped")

    async def _monitor_jobs(self) -> None:
        """Monitor job queue and start new jobs as capacity allows."""
        while self.is_running:
            try:
                # Check if we can start more jobs
                if len(self.running_tasks) < self.max_concurrent_jobs:
                    # Get next job from queue
                    job_request = await self.job_queue_manager.get_next_job()

                    if job_request:
                        job_id = job_request.job_id
                        logger.info(f"Starting background execution for job {job_id}")

                        # Create and start job task
                        task = asyncio.create_task(
                            self._execute_job_with_monitoring(job_id, job_request)
                        )
                        self.running_tasks[job_id] = task

                # Clean up completed tasks
                completed_jobs = [
                    job_id for job_id, task in self.running_tasks.items()
                    if task.done()
                ]

                for job_id in completed_jobs:
                    task = self.running_tasks.pop(job_id)
                    try:
                        await task  # Get any exceptions
                        logger.info(f"Job {job_id} task completed successfully")
                    except Exception as e:
                        logger.error(f"Job {job_id} task failed: {e}")

                # Wait before next check
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error in job monitor: {e}")
                await asyncio.sleep(5)

    async def _execute_job_with_monitoring(self, job_id: str, job_request) -> None:
        """Execute a job with progress monitoring and error handling."""
        try:
            # Update job status to running
            await self.job_storage.update_job_status(
                job_id,
                status=JobState.RUNNING,
                started_at=datetime.utcnow()
            )

            # Execute the job
            result = await self.job_executor.execute_job(job_request)

            # Save result and update status
            await self.job_storage.save_job_result(job_id, result)
            await self.job_storage.update_job_status(
                job_id,
                status=JobState.COMPLETED,
                progress=100.0,
                completed_at=datetime.utcnow()
            )

            logger.info(f"Job {job_id} completed successfully")

        except asyncio.CancelledError:
            # Job was cancelled
            await self.job_storage.update_job_status(
                job_id,
                status=JobState.CANCELLED,
                completed_at=datetime.utcnow()
            )
            logger.info(f"Job {job_id} was cancelled")
            raise

        except Exception as e:
            # Job failed
            logger.error(f"Job {job_id} failed: {e}")

            # Save error information
            from sgr_deep_research.api.models import JobError, ErrorType
            error = JobError(
                job_id=job_id,
                error_type=ErrorType.INTERNAL,
                error_message=str(e),
                error_details={"exception_type": type(e).__name__},
                retry_count=0,
                is_retryable=False,
                occurred_at=datetime.utcnow()
            )

            await self.job_storage.save_job_error(job_id, error)
            await self.job_storage.update_job_status(
                job_id,
                status=JobState.FAILED,
                completed_at=datetime.utcnow()
            )

    async def _cleanup_completed_jobs(self) -> None:
        """Periodically clean up old completed jobs."""
        while self.is_running:
            try:
                # Clean up jobs older than 24 hours
                cutoff_time = datetime.utcnow() - timedelta(hours=24)

                # Get all completed jobs
                completed_jobs = await self.job_storage.list_jobs(
                    status=JobState.COMPLETED
                )

                for job in completed_jobs:
                    if job.completed_at and job.completed_at < cutoff_time:
                        logger.info(f"Cleaning up old completed job {job.job_id}")
                        await self.job_storage.delete_job(job.job_id)

                # Wait for next cleanup cycle
                await asyncio.sleep(self.cleanup_interval)

            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)

    async def get_status(self) -> Dict:
        """Get current status of the background task runner."""
        return {
            "is_running": self.is_running,
            "running_jobs": len(self.running_tasks),
            "max_concurrent_jobs": self.max_concurrent_jobs,
            "running_job_ids": list(self.running_tasks.keys())
        }

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a specific running job."""
        if job_id in self.running_tasks:
            task = self.running_tasks[job_id]
            task.cancel()
            logger.info(f"Cancelled job {job_id}")
            return True
        return False


# Global background task runner instance
_background_runner: Optional[BackgroundTaskRunner] = None


async def get_background_runner() -> BackgroundTaskRunner:
    """Get or create the global background task runner."""
    global _background_runner

    if _background_runner is None:
        from sgr_deep_research.core.job_storage import JobStorage
        from sgr_deep_research.core.job_queue_manager import JobQueueManager
        from sgr_deep_research.core.job_executor import JobExecutor

        job_storage = JobStorage()
        job_queue_manager = JobQueueManager()
        job_executor = JobExecutor(job_storage, job_queue_manager)

        _background_runner = BackgroundTaskRunner(
            job_storage=job_storage,
            job_queue_manager=job_queue_manager,
            job_executor=job_executor
        )

        # Start the runner
        await _background_runner.start()

    return _background_runner


async def shutdown_background_runner() -> None:
    """Shutdown the global background task runner."""
    global _background_runner

    if _background_runner is not None:
        await _background_runner.stop()
        _background_runner = None