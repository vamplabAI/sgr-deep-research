"""Job lifecycle management for SGR Deep Research.

This module handles the complete lifecycle of research jobs from submission
to completion, including state transitions, progress tracking, and cleanup.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum

from sgr_deep_research.api.models import (
    JobRequest, JobStatus, JobResult, JobError, JobState,
    ErrorType, ExecutionMetrics, ResearchSource
)
from sgr_deep_research.core.job_storage import JobStorage
from sgr_deep_research.core.job_queue_manager import JobQueueManager

logger = logging.getLogger(__name__)


class JobPhase(Enum):
    """Phases of job execution."""
    QUEUED = "queued"
    STARTING = "starting"
    RESEARCHING = "researching"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobLifecycleManager:
    """Manages the complete lifecycle of research jobs."""

    def __init__(
        self,
        job_storage: JobStorage,
        job_queue_manager: JobQueueManager,
        max_execution_time: timedelta = timedelta(hours=2),
        progress_update_interval: int = 5
    ):
        self.job_storage = job_storage
        self.job_queue_manager = job_queue_manager
        self.max_execution_time = max_execution_time
        self.progress_update_interval = progress_update_interval

        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self.is_running = False

    async def start(self) -> None:
        """Start the lifecycle manager."""
        if self.is_running:
            return

        self.is_running = True
        logger.info("Starting job lifecycle manager")

        # Start background tasks
        self._cleanup_task = asyncio.create_task(self._cleanup_stale_jobs())
        self._monitor_task = asyncio.create_task(self._monitor_timeouts())

    async def stop(self) -> None:
        """Stop the lifecycle manager."""
        if not self.is_running:
            return

        logger.info("Stopping job lifecycle manager")
        self.is_running = False

        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._monitor_task:
            self._monitor_task.cancel()

        # Wait for tasks to complete
        if self._cleanup_task:
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        if self._monitor_task:
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    async def submit_job(self, request: JobRequest) -> JobStatus:
        """Submit a new job and initialize its lifecycle."""
        # Create initial job status
        job_status = JobStatus(
            job_id=request.job_id,
            status=JobState.PENDING,
            progress=0.0,
            current_step="Job submitted, waiting in queue",
            steps_completed=0,
            total_steps=self._estimate_total_steps(request),
            created_at=datetime.utcnow(),
            estimated_completion=self._estimate_completion_time(request)
        )

        # Store job status
        await self.job_storage.save_job_status(job_status)

        # Add to queue
        await self.job_queue_manager.add_job(request)

        # Track active job
        self.active_jobs[request.job_id] = {
            "request": request,
            "phase": JobPhase.QUEUED,
            "started_at": datetime.utcnow(),
            "last_update": datetime.utcnow()
        }

        logger.info(f"Job {request.job_id} submitted and added to lifecycle tracking")
        return job_status

    async def start_job_execution(self, job_id: str) -> bool:
        """Start execution of a queued job."""
        try:
            # Update job status
            await self._update_job_progress(
                job_id,
                status=JobState.RUNNING,
                progress=5.0,
                current_step="Starting job execution",
                phase=JobPhase.STARTING,
                started_at=datetime.utcnow()
            )

            logger.info(f"Job {job_id} execution started")
            return True

        except Exception as e:
            logger.error(f"Failed to start job {job_id}: {e}")
            await self._fail_job(job_id, ErrorType.INTERNAL, str(e))
            return False

    async def update_job_phase(
        self,
        job_id: str,
        phase: JobPhase,
        progress: float,
        step_description: str,
        sources_found: int = 0
    ) -> None:
        """Update job phase and progress."""
        try:
            await self._update_job_progress(
                job_id,
                progress=progress,
                current_step=step_description,
                phase=phase,
                sources_found=sources_found
            )

            logger.debug(f"Job {job_id} updated: {phase.value} - {progress}%")

        except Exception as e:
            logger.error(f"Failed to update job {job_id} phase: {e}")

    async def complete_job(
        self,
        job_id: str,
        result: JobResult
    ) -> None:
        """Complete a job with results."""
        try:
            # Save result
            await self.job_storage.save_job_result(job_id, result)

            # Update status
            await self._update_job_progress(
                job_id,
                status=JobState.COMPLETED,
                progress=100.0,
                current_step="Job completed successfully",
                phase=JobPhase.COMPLETED,
                completed_at=datetime.utcnow()
            )

            # Remove from active tracking
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]

            logger.info(f"Job {job_id} completed successfully")

        except Exception as e:
            logger.error(f"Failed to complete job {job_id}: {e}")
            await self._fail_job(job_id, ErrorType.INTERNAL, str(e))

    async def fail_job(
        self,
        job_id: str,
        error_type: ErrorType,
        error_message: str,
        error_details: Dict[str, Any] = None,
        is_retryable: bool = False
    ) -> None:
        """Fail a job with error information."""
        await self._fail_job(job_id, error_type, error_message, error_details, is_retryable)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running or queued job."""
        try:
            # Check if job exists
            job_status = await self.job_storage.get_job_status(job_id)
            if not job_status:
                return False

            # Can only cancel pending or running jobs
            if job_status.status not in [JobState.PENDING, JobState.RUNNING]:
                return False

            # Update status
            await self._update_job_progress(
                job_id,
                status=JobState.CANCELLED,
                current_step="Job cancelled by user",
                phase=JobPhase.CANCELLED,
                completed_at=datetime.utcnow()
            )

            # Remove from queue if pending
            if job_status.status == JobState.PENDING:
                await self.job_queue_manager.remove_job(job_id)

            # Remove from active tracking
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]

            logger.info(f"Job {job_id} cancelled")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False

    async def get_job_status_with_lifecycle(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status with lifecycle information."""
        job_status = await self.job_storage.get_job_status(job_id)
        if not job_status:
            return None

        lifecycle_info = self.active_jobs.get(job_id, {})

        return {
            "job_status": job_status,
            "lifecycle": {
                "phase": lifecycle_info.get("phase", JobPhase.COMPLETED).value,
                "execution_time": (
                    datetime.utcnow() - lifecycle_info["started_at"]
                ).total_seconds() if "started_at" in lifecycle_info else None,
                "is_active": job_id in self.active_jobs
            }
        }

    async def _update_job_progress(
        self,
        job_id: str,
        status: JobState = None,
        progress: float = None,
        current_step: str = None,
        phase: JobPhase = None,
        sources_found: int = None,
        started_at: datetime = None,
        completed_at: datetime = None
    ) -> None:
        """Update job progress and status."""
        # Get current status
        job_status = await self.job_storage.get_job_status(job_id)
        if not job_status:
            logger.error(f"Job {job_id} not found for progress update")
            return

        # Update fields
        if status is not None:
            job_status.status = status
        if progress is not None:
            job_status.progress = progress
            job_status.steps_completed = int((progress / 100) * job_status.total_steps)
        if current_step is not None:
            job_status.current_step = current_step
        if sources_found is not None:
            job_status.sources_found = sources_found
        if started_at is not None:
            job_status.started_at = started_at
        if completed_at is not None:
            job_status.completed_at = completed_at

        # Update active job tracking
        if job_id in self.active_jobs:
            if phase is not None:
                self.active_jobs[job_id]["phase"] = phase
            self.active_jobs[job_id]["last_update"] = datetime.utcnow()

        # Save updated status
        await self.job_storage.save_job_status(job_status)

    async def _fail_job(
        self,
        job_id: str,
        error_type: ErrorType,
        error_message: str,
        error_details: Dict[str, Any] = None,
        is_retryable: bool = False
    ) -> None:
        """Mark a job as failed with error information."""
        try:
            # Create error record
            error = JobError(
                job_id=job_id,
                error_type=error_type,
                error_message=error_message,
                error_details=error_details or {},
                retry_count=0,
                is_retryable=is_retryable,
                occurred_at=datetime.utcnow()
            )

            # Save error
            await self.job_storage.save_job_error(job_id, error)

            # Update status
            await self._update_job_progress(
                job_id,
                status=JobState.FAILED,
                current_step=f"Job failed: {error_message}",
                phase=JobPhase.FAILED,
                completed_at=datetime.utcnow()
            )

            # Remove from active tracking
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]

            logger.error(f"Job {job_id} failed: {error_message}")

        except Exception as e:
            logger.error(f"Failed to record job failure for {job_id}: {e}")

    def _estimate_total_steps(self, request: JobRequest) -> int:
        """Estimate total steps based on request parameters."""
        base_steps = 6  # Base SGR steps

        if request.deep_level > 0:
            # Deep mode scaling
            return base_steps * (3 * request.deep_level + 1)

        return base_steps

    def _estimate_completion_time(self, request: JobRequest) -> datetime:
        """Estimate completion time based on request parameters."""
        base_minutes = 5  # Base execution time

        if request.deep_level > 0:
            # Deep mode takes longer
            multiplier = request.deep_level * 3
            base_minutes *= multiplier

        return datetime.utcnow() + timedelta(minutes=base_minutes)

    async def _cleanup_stale_jobs(self) -> None:
        """Clean up stale job tracking entries."""
        while self.is_running:
            try:
                now = datetime.utcnow()
                cutoff = now - timedelta(hours=24)

                stale_jobs = [
                    job_id for job_id, info in self.active_jobs.items()
                    if info.get("last_update", now) < cutoff
                ]

                for job_id in stale_jobs:
                    logger.info(f"Cleaning up stale job tracking for {job_id}")
                    del self.active_jobs[job_id]

                await asyncio.sleep(3600)  # Check every hour

            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error

    async def _monitor_timeouts(self) -> None:
        """Monitor jobs for timeout and handle accordingly."""
        while self.is_running:
            try:
                now = datetime.utcnow()

                for job_id, info in list(self.active_jobs.items()):
                    started_at = info.get("started_at")
                    if started_at and (now - started_at) > self.max_execution_time:
                        logger.warning(f"Job {job_id} timed out after {self.max_execution_time}")
                        await self._fail_job(
                            job_id,
                            ErrorType.TIMEOUT,
                            f"Job exceeded maximum execution time of {self.max_execution_time}"
                        )

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Error in timeout monitor: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error