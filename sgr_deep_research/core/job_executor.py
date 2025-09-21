"""Job execution service for running research jobs.

This module provides the JobExecutor service for executing research jobs
using the existing SGR agent infrastructure.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from ..api.models import (
    JobRequest, JobStatus, JobResult, JobError, JobState,
    ResearchSource, ExecutionMetrics, ErrorType, ErrorSeverity,
    SourceType, SourceStatus
)
from .job_storage import get_job_storage
from .agents.base_agent import BaseAgent
from .agents.sgr_tools_agent import SGRToolCallingResearchAgent
from .agents.sgr_agent import SGRAgent
from .agents.tools_agent import ToolCallingResearchAgent

logger = logging.getLogger(__name__)


class JobExecutionError(Exception):
    """Exception raised during job execution."""
    pass


class JobExecutor:
    """Service for executing research jobs using SGR agents.

    Handles job execution lifecycle, progress tracking, error handling,
    and result generation.
    """

    def __init__(self, max_concurrent_jobs: int = 5):
        """Initialize job executor.

        Args:
            max_concurrent_jobs: Maximum number of concurrent job executions
        """
        self.max_concurrent_jobs = max_concurrent_jobs
        self.storage = get_job_storage()

        # Track running jobs
        self._running_jobs: Dict[str, asyncio.Task] = {}
        self._job_cancellation_events: Dict[str, asyncio.Event] = {}

        # Agent registry
        self._agent_registry = {
            "sgr": SGRAgent,
            "sgr-tools": SGRToolCallingResearchAgent,
            "tools": ToolCallingResearchAgent,
        }

        # Progress callbacks
        self._progress_callbacks: Dict[str, List[Callable]] = {}

        # Execution statistics
        self._execution_stats = {
            "jobs_started": 0,
            "jobs_completed": 0,
            "jobs_failed": 0,
            "jobs_cancelled": 0,
            "total_execution_time": 0.0
        }

    def register_agent_type(self, agent_type: str, agent_class: type):
        """Register a new agent type.

        Args:
            agent_type: Agent type identifier
            agent_class: Agent class implementing BaseAgent interface
        """
        self._agent_registry[agent_type] = agent_class

    def register_progress_callback(self, job_id: str, callback: Callable):
        """Register a progress callback for a job.

        Args:
            job_id: Job identifier
            callback: Callback function that receives (job_id, progress, step)
        """
        if job_id not in self._progress_callbacks:
            self._progress_callbacks[job_id] = []
        self._progress_callbacks[job_id].append(callback)

    def unregister_progress_callbacks(self, job_id: str):
        """Remove all progress callbacks for a job.

        Args:
            job_id: Job identifier
        """
        self._progress_callbacks.pop(job_id, None)

    async def _notify_progress_callbacks(self, job_id: str, progress: float, step: str):
        """Notify all registered progress callbacks.

        Args:
            job_id: Job identifier
            progress: Current progress (0.0-100.0)
            step: Current step description
        """
        callbacks = self._progress_callbacks.get(job_id, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(job_id, progress, step)
                else:
                    callback(job_id, progress, step)
            except Exception as e:
                logger.warning(f"Progress callback failed for job {job_id}: {e}")

    async def can_start_job(self) -> bool:
        """Check if a new job can be started.

        Returns:
            bool: True if job can be started
        """
        active_jobs = len(self._running_jobs)
        return active_jobs < self.max_concurrent_jobs

    async def start_job(self, job_request: JobRequest) -> str:
        """Start executing a research job.

        Args:
            job_request: Job request parameters

        Returns:
            str: Job ID

        Raises:
            JobExecutionError: If job cannot be started
        """
        if not await self.can_start_job():
            raise JobExecutionError("Maximum concurrent jobs reached")

        # Create job in storage
        job_status = await self.storage.create_job(job_request)
        job_id = job_status.job_id

        logger.info(f"Starting job execution: {job_id}")

        # Create cancellation event
        self._job_cancellation_events[job_id] = asyncio.Event()

        # Start execution task
        task = asyncio.create_task(
            self._execute_job(job_request, job_status),
            name=f"job-{job_id}"
        )
        self._running_jobs[job_id] = task

        # Update statistics
        self._execution_stats["jobs_started"] += 1

        return job_id

    async def cancel_job(self, job_id: str, reason: str = "User requested cancellation") -> bool:
        """Cancel a running job.

        Args:
            job_id: Job identifier
            reason: Cancellation reason

        Returns:
            bool: True if job was cancelled, False if not running

        Raises:
            JobExecutionError: If cancellation fails
        """
        # Check if job is running
        if job_id not in self._running_jobs:
            # Try to cancel in storage if it's pending
            try:
                await self.storage.cancel_job(job_id, reason)
                return True
            except Exception:
                return False

        logger.info(f"Cancelling job: {job_id} - {reason}")

        try:
            # Signal cancellation
            if job_id in self._job_cancellation_events:
                self._job_cancellation_events[job_id].set()

            # Cancel the task
            task = self._running_jobs[job_id]
            task.cancel()

            # Wait for task to complete
            try:
                await asyncio.wait_for(task, timeout=30.0)
            except asyncio.TimeoutError:
                logger.warning(f"Job {job_id} cancellation timed out")

            # Update job status in storage
            await self.storage.cancel_job(job_id, reason)

            # Update statistics
            self._execution_stats["jobs_cancelled"] += 1

            return True

        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            raise JobExecutionError(f"Failed to cancel job: {e}")

        finally:
            # Cleanup
            self._cleanup_job(job_id)

    async def get_running_jobs(self) -> List[str]:
        """Get list of currently running job IDs.

        Returns:
            List[str]: List of running job IDs
        """
        return list(self._running_jobs.keys())

    async def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics.

        Returns:
            Dict: Execution statistics
        """
        stats = self._execution_stats.copy()
        stats["currently_running"] = len(self._running_jobs)
        stats["max_concurrent"] = self.max_concurrent_jobs
        return stats

    def _cleanup_job(self, job_id: str):
        """Clean up job tracking data.

        Args:
            job_id: Job identifier
        """
        self._running_jobs.pop(job_id, None)
        self._job_cancellation_events.pop(job_id, None)
        self.unregister_progress_callbacks(job_id)

    def _create_agent(self, job_request: JobRequest) -> BaseAgent:
        """Create agent instance for job execution.

        Args:
            job_request: Job request parameters

        Returns:
            BaseAgent: Agent instance

        Raises:
            JobExecutionError: If agent type is not supported
        """
        agent_type = job_request.agent_type

        if agent_type not in self._agent_registry:
            raise JobExecutionError(f"Unsupported agent type: {agent_type}")

        agent_class = self._agent_registry[agent_type]

        try:
            # Create agent with job parameters
            agent = agent_class(
                task=job_request.query,
                max_iterations=job_request.get_effective_iterations(),
                max_searches=job_request.get_effective_searches()
            )

            return agent

        except Exception as e:
            raise JobExecutionError(f"Failed to create agent: {e}")

    async def _execute_job(self, job_request: JobRequest, job_status: JobStatus):
        """Execute a research job.

        Args:
            job_request: Job request parameters
            job_status: Initial job status
        """
        job_id = job_status.job_id
        start_time = datetime.utcnow()

        try:
            logger.info(f"Executing job {job_id}: {job_request.query}")

            # Mark job as started
            await self.storage.start_job(job_id)
            await self._notify_progress_callbacks(job_id, 0.0, "Starting job execution")

            # Create agent
            agent = self._create_agent(job_request)

            # Set up progress tracking
            await self._setup_agent_progress_tracking(agent, job_id, job_request)

            # Execute research with cancellation support
            result = await self._execute_with_cancellation(agent, job_id, job_request)

            # Process and save results
            await self._process_and_save_results(job_id, result, start_time, job_request)

            # Mark job as completed
            await self.storage.complete_job(job_id)
            await self._notify_progress_callbacks(job_id, 100.0, "Job completed successfully")

            # Update statistics
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self._execution_stats["jobs_completed"] += 1
            self._execution_stats["total_execution_time"] += execution_time

            logger.info(f"Job {job_id} completed successfully in {execution_time:.2f}s")

        except asyncio.CancelledError:
            logger.info(f"Job {job_id} was cancelled")
            await self._handle_job_cancellation(job_id, start_time)

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            await self._handle_job_error(job_id, e, start_time)

        finally:
            # Cleanup
            self._cleanup_job(job_id)

    async def _setup_agent_progress_tracking(self, agent: BaseAgent, job_id: str, job_request: JobRequest):
        """Set up progress tracking for the agent.

        Args:
            agent: Agent instance
            job_id: Job identifier
            job_request: Job request parameters
        """
        total_steps = job_request.get_effective_iterations()

        async def progress_callback(step: int, description: str):
            """Agent progress callback."""
            if step >= 0:
                progress = min(95.0, (step / total_steps) * 100) if total_steps > 0 else 0.0
                await self.storage.update_job_progress(
                    job_id, progress, description, step
                )
                await self._notify_progress_callbacks(job_id, progress, description)

        # Set up agent progress callback if supported
        if hasattr(agent, 'set_progress_callback'):
            agent.set_progress_callback(progress_callback)

    async def _execute_with_cancellation(self, agent: BaseAgent, job_id: str, job_request: JobRequest) -> Dict[str, Any]:
        """Execute agent research with cancellation support.

        Args:
            agent: Agent instance
            job_id: Job identifier
            job_request: Job request parameters

        Returns:
            Dict: Research results

        Raises:
            asyncio.CancelledError: If job was cancelled
        """
        cancellation_event = self._job_cancellation_events.get(job_id)

        # Create execution task
        execution_task = asyncio.create_task(
            agent.research(job_request.query)
        )

        if cancellation_event:
            # Wait for either completion or cancellation
            cancellation_task = asyncio.create_task(cancellation_event.wait())

            try:
                done, pending = await asyncio.wait(
                    [execution_task, cancellation_task],
                    return_when=asyncio.FIRST_COMPLETED
                )

                # Cancel pending tasks
                for task in pending:
                    task.cancel()

                if cancellation_task in done:
                    # Job was cancelled
                    execution_task.cancel()
                    raise asyncio.CancelledError("Job was cancelled")

                # Get execution result
                return await execution_task

            except asyncio.CancelledError:
                execution_task.cancel()
                raise

        else:
            # Execute without cancellation support
            return await execution_task

    async def _process_and_save_results(self, job_id: str, result: Dict[str, Any],
                                      start_time: datetime, job_request: JobRequest):
        """Process agent results and save to storage.

        Args:
            job_id: Job identifier
            result: Agent execution results
            start_time: Job start time
            job_request: Original job request
        """
        end_time = datetime.utcnow()
        duration = end_time - start_time

        # Create research sources
        sources = []
        if "sources" in result and result["sources"]:
            for i, source_data in enumerate(result["sources"], 1):
                source = ResearchSource(
                    number=i,
                    url=source_data.get("url", ""),
                    title=source_data.get("title", ""),
                    content_excerpt=source_data.get("content", "")[:2000],
                    confidence_score=source_data.get("confidence", 0.0),
                    source_type=self._determine_source_type(source_data.get("url", "")),
                    status=SourceStatus.ANALYZED,
                    discovered_at=start_time,
                    analyzed_at=end_time
                )
                source.update_domain()
                sources.append(source)

        # Create execution metrics
        metrics = ExecutionMetrics(
            total_duration_seconds=duration.total_seconds(),
            execution_time_seconds=duration.total_seconds(),
            api_calls_made=result.get("api_calls", 0),
            tokens_consumed=result.get("tokens_used", 0),
            search_operations=result.get("searches_made", 0),
            sources_processed=len(sources),
            research_depth_achieved=job_request.deep_level,
            started_at=start_time,
            completed_at=end_time
        )

        # Estimate costs (simplified)
        estimated_cost = self._estimate_job_cost(metrics, job_request)
        metrics.estimated_cost = estimated_cost

        # Create job result
        job_result = JobResult(
            job_id=job_id,
            final_answer=result.get("final_answer", ""),
            sources=sources,
            metrics=metrics,
            quality_score=self._calculate_quality_score(result, sources),
            research_depth=job_request.deep_level,
            key_insights=result.get("key_insights", []),
            completion_reason="success"
        )

        # Save result
        await self.storage.save_result(job_result)

        logger.info(f"Saved results for job {job_id}: {len(sources)} sources, "
                   f"{metrics.total_duration_seconds:.1f}s duration")

    async def _handle_job_cancellation(self, job_id: str, start_time: datetime):
        """Handle job cancellation.

        Args:
            job_id: Job identifier
            start_time: Job start time
        """
        try:
            # Create cancellation error for tracking
            error = JobError(
                job_id=job_id,
                error_type=ErrorType.USER_CANCELLED,
                error_message="Job was cancelled by user request",
                severity=ErrorSeverity.LOW,
                occurred_at=datetime.utcnow(),
                progress_at_failure=await self._get_current_progress(job_id)
            )

            # Update job status (will be handled by storage)
            await self.storage.save_error(error)

        except Exception as e:
            logger.error(f"Failed to handle cancellation for job {job_id}: {e}")

    async def _handle_job_error(self, job_id: str, error: Exception, start_time: datetime):
        """Handle job execution error.

        Args:
            job_id: Job identifier
            error: Exception that occurred
            start_time: Job start time
        """
        try:
            # Determine error type and severity
            error_type, severity = self._classify_error(error)

            # Create error record
            job_error = JobError(
                job_id=job_id,
                error_type=error_type,
                error_message=str(error)[:1000],
                severity=severity,
                occurred_at=datetime.utcnow(),
                progress_at_failure=await self._get_current_progress(job_id),
                is_retryable=self._is_retryable_error(error_type),
                stack_trace=self._get_stack_trace(error)
            )

            # Add suggested actions
            self._add_error_suggestions(job_error, error)

            # Save error and mark job as failed
            await self.storage.fail_job(job_id, job_error)

            # Update statistics
            self._execution_stats["jobs_failed"] += 1

        except Exception as e:
            logger.error(f"Failed to handle error for job {job_id}: {e}")

    def _determine_source_type(self, url: str) -> SourceType:
        """Determine source type from URL.

        Args:
            url: Source URL

        Returns:
            SourceType: Detected source type
        """
        url_lower = url.lower()

        if "arxiv.org" in url_lower or "pubmed" in url_lower:
            return SourceType.ACADEMIC_PAPER
        elif "youtube.com" in url_lower or "youtu.be" in url_lower:
            return SourceType.VIDEO
        elif any(news in url_lower for news in ["news", "reuters", "cnn", "bbc"]):
            return SourceType.NEWS_ARTICLE
        elif "blog" in url_lower or "medium.com" in url_lower:
            return SourceType.BLOG_POST
        elif any(doc in url_lower for doc in ["docs", "documentation", "manual"]):
            return SourceType.DOCUMENTATION
        else:
            return SourceType.WEB_PAGE

    def _estimate_job_cost(self, metrics: ExecutionMetrics, job_request: JobRequest) -> float:
        """Estimate job execution cost.

        Args:
            metrics: Execution metrics
            job_request: Original job request

        Returns:
            float: Estimated cost in USD
        """
        # Simplified cost calculation
        base_cost = 0.01  # Base cost per job

        # Token costs (approximation)
        token_cost = metrics.tokens_consumed * 0.00002  # ~$0.02 per 1K tokens

        # Search costs
        search_cost = metrics.search_operations * 0.01  # ~$0.01 per search

        # Deep research multiplier
        depth_multiplier = 1.0 + (job_request.deep_level * 0.5)

        total_cost = (base_cost + token_cost + search_cost) * depth_multiplier
        return round(total_cost, 3)

    def _calculate_quality_score(self, result: Dict[str, Any], sources: List[ResearchSource]) -> float:
        """Calculate research quality score.

        Args:
            result: Research results
            sources: Research sources

        Returns:
            float: Quality score (0.0-10.0)
        """
        score = 5.0  # Base score

        # Content length bonus
        final_answer = result.get("final_answer", "")
        if len(final_answer) > 1000:
            score += 1.0
        elif len(final_answer) > 500:
            score += 0.5

        # Source diversity bonus
        if len(sources) >= 10:
            score += 1.5
        elif len(sources) >= 5:
            score += 1.0

        # Academic source bonus
        academic_sources = sum(1 for s in sources if s.is_academic_source())
        if academic_sources > 0:
            score += min(1.0, academic_sources * 0.2)

        return min(10.0, round(score, 1))

    def _classify_error(self, error: Exception) -> tuple[ErrorType, ErrorSeverity]:
        """Classify error type and severity.

        Args:
            error: Exception that occurred

        Returns:
            tuple: (ErrorType, ErrorSeverity)
        """
        if isinstance(error, asyncio.TimeoutError):
            return ErrorType.TIMEOUT, ErrorSeverity.MEDIUM
        elif "network" in str(error).lower() or "connection" in str(error).lower():
            return ErrorType.NETWORK_ERROR, ErrorSeverity.MEDIUM
        elif "rate limit" in str(error).lower():
            return ErrorType.RATE_LIMIT, ErrorSeverity.LOW
        elif "authentication" in str(error).lower() or "api key" in str(error).lower():
            return ErrorType.AUTHENTICATION_ERROR, ErrorSeverity.HIGH
        else:
            return ErrorType.UNKNOWN_ERROR, ErrorSeverity.HIGH

    def _is_retryable_error(self, error_type: ErrorType) -> bool:
        """Check if error type is retryable.

        Args:
            error_type: Error type

        Returns:
            bool: True if retryable
        """
        retryable_types = {
            ErrorType.NETWORK_ERROR,
            ErrorType.TIMEOUT,
            ErrorType.RATE_LIMIT,
            ErrorType.RESOURCE_ERROR
        }
        return error_type in retryable_types

    def _get_stack_trace(self, error: Exception) -> str:
        """Get stack trace from exception.

        Args:
            error: Exception

        Returns:
            str: Stack trace
        """
        import traceback
        return traceback.format_exc()[:10000]  # Limit size

    def _add_error_suggestions(self, job_error: JobError, error: Exception):
        """Add suggested actions for error resolution.

        Args:
            job_error: Job error object
            error: Original exception
        """
        error_str = str(error).lower()

        if "network" in error_str or "connection" in error_str:
            job_error.add_suggested_action("Check network connectivity")
            job_error.add_suggested_action("Verify firewall settings")
            job_error.add_suggested_action("Try again in a few minutes")

        elif "timeout" in error_str:
            job_error.add_suggested_action("Reduce research depth level")
            job_error.add_suggested_action("Increase timeout settings")
            job_error.add_suggested_action("Try with a more specific query")

        elif "rate limit" in error_str:
            job_error.add_suggested_action("Wait before submitting new jobs")
            job_error.add_suggested_action("Check API quota limits")

        elif "api key" in error_str or "authentication" in error_str:
            job_error.add_suggested_action("Verify API credentials")
            job_error.add_suggested_action("Check configuration settings")

    async def _get_current_progress(self, job_id: str) -> float:
        """Get current job progress.

        Args:
            job_id: Job identifier

        Returns:
            float: Current progress percentage
        """
        try:
            job_status = await self.storage.get_job(job_id)
            return job_status.progress if job_status else 0.0
        except Exception:
            return 0.0

    async def close(self):
        """Close executor and cleanup resources."""
        # Cancel all running jobs
        running_jobs = list(self._running_jobs.keys())
        for job_id in running_jobs:
            try:
                await self.cancel_job(job_id, "System shutdown")
            except Exception as e:
                logger.warning(f"Failed to cancel job {job_id} during shutdown: {e}")

        # Clear tracking data
        self._running_jobs.clear()
        self._job_cancellation_events.clear()
        self._progress_callbacks.clear()


# Global executor instance
_executor_instance: Optional[JobExecutor] = None


def get_job_executor() -> JobExecutor:
    """Get the global job executor instance."""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = JobExecutor()
    return _executor_instance


async def close_job_executor():
    """Close the global job executor instance."""
    global _executor_instance
    if _executor_instance:
        await _executor_instance.close()
        _executor_instance = None