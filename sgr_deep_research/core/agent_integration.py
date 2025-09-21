"""Agent integration for job execution.

This module provides integration between the job management system
and the SGR agents for executing research tasks.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from sgr_deep_research.api.models import (
    JobRequest, JobResult, ExecutionMetrics, ResearchSource,
    AgentType, ErrorType
)
from sgr_deep_research.core.agents import BaseAgent
from sgr_deep_research.core.agents.sgr_agent import SGRAgent
from sgr_deep_research.core.agents.sgr_tools_agent import SGRToolCallingResearchAgent
from sgr_deep_research.core.agents.sgr_auto_tools_agent import SGRAutoToolsAgent
from sgr_deep_research.core.agents.sgr_so_tools_agent import SGRStructuredOutputToolsAgent
from sgr_deep_research.core.agents.tools_agent import ToolCallingResearchAgent
from sgr_deep_research.core.job_lifecycle import JobLifecycleManager, JobPhase

logger = logging.getLogger(__name__)


class AgentJobExecutor:
    """Executes jobs using SGR agents."""

    def __init__(self, lifecycle_manager: Optional[JobLifecycleManager] = None):
        self.lifecycle_manager = lifecycle_manager
        self.agent_classes = {
            AgentType.SGR: SGRAgent,
            AgentType.SGR_TOOLS: SGRToolCallingResearchAgent,
            AgentType.SGR_AUTO_TOOLS: SGRAutoToolsAgent,
            AgentType.SGR_SO_TOOLS: SGRStructuredOutputToolsAgent,
            AgentType.TOOLS: ToolCallingResearchAgent,
        }

    async def execute_job(self, request: JobRequest) -> JobResult:
        """Execute a research job using the appropriate agent."""
        start_time = datetime.utcnow()

        try:
            # Update job phase to starting
            if self.lifecycle_manager:
                await self.lifecycle_manager.update_job_phase(
                    request.job_id,
                    JobPhase.STARTING,
                    10.0,
                    "Initializing research agent"
                )

            # Create agent
            agent = await self._create_agent(request)

            # Update phase to researching
            if self.lifecycle_manager:
                await self.lifecycle_manager.update_job_phase(
                    request.job_id,
                    JobPhase.RESEARCHING,
                    20.0,
                    "Starting research process"
                )

            # Execute research with progress monitoring
            result = await self._execute_with_monitoring(agent, request)

            # Update phase to finalizing
            if self.lifecycle_manager:
                await self.lifecycle_manager.update_job_phase(
                    request.job_id,
                    JobPhase.FINALIZING,
                    90.0,
                    "Finalizing research report"
                )

            # Calculate execution metrics
            execution_time = datetime.utcnow() - start_time
            metrics = await self._calculate_metrics(agent, execution_time)

            # Create job result
            job_result = JobResult(
                job_id=request.job_id,
                final_answer=result.get("final_answer", ""),
                report_path=None,  # TODO: Implement report saving
                sources=await self._extract_sources(agent),
                metrics=metrics,
                agent_conversation=result.get("conversation", []),
                artifacts=[]  # TODO: Implement artifacts
            )

            logger.info(f"Job {request.job_id} executed successfully")
            return job_result

        except Exception as e:
            logger.error(f"Job {request.job_id} execution failed: {e}")

            if self.lifecycle_manager:
                await self.lifecycle_manager.fail_job(
                    request.job_id,
                    ErrorType.INTERNAL,
                    str(e),
                    {"exception_type": type(e).__name__}
                )

            raise

    async def _create_agent(self, request: JobRequest) -> BaseAgent:
        """Create an agent instance based on the request."""
        agent_class = self.agent_classes.get(request.agent_type)
        if not agent_class:
            raise ValueError(f"Unknown agent type: {request.agent_type}")

        # Configure agent parameters based on request
        agent_config = self._build_agent_config(request)

        try:
            agent = agent_class(task=request.query, **agent_config)
            logger.info(f"Created {request.agent_type.value} agent for job {request.job_id}")
            return agent

        except Exception as e:
            logger.error(f"Failed to create agent {request.agent_type.value}: {e}")
            raise ValueError(f"Failed to create agent: {e}")

    def _build_agent_config(self, request: JobRequest) -> Dict[str, Any]:
        """Build agent configuration from job request."""
        config = {}

        # Configure based on deep level
        if request.deep_level > 0:
            # Deep mode configuration
            base_steps = 6
            config["max_iterations"] = base_steps * (3 * request.deep_level + 1)
            config["max_searches"] = 4 * (request.deep_level + 1)
        else:
            # Normal mode
            config["max_iterations"] = 6
            config["max_searches"] = 4

        # Add metadata as agent configuration
        if request.metadata:
            config.update(request.metadata)

        return config

    async def _execute_with_monitoring(
        self,
        agent: BaseAgent,
        request: JobRequest
    ) -> Dict[str, Any]:
        """Execute agent with progress monitoring."""
        # Create monitoring task
        monitor_task = None
        if self.lifecycle_manager:
            monitor_task = asyncio.create_task(
                self._monitor_agent_progress(agent, request.job_id)
            )

        try:
            # Execute agent
            await agent.execute()

            # Get results
            result = {
                "final_answer": agent.get_final_answer(),
                "conversation": agent.get_conversation_history(),
                "sources": agent.get_sources()
            }

            return result

        finally:
            # Cancel monitoring task
            if monitor_task:
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass

    async def _monitor_agent_progress(self, agent: BaseAgent, job_id: str) -> None:
        """Monitor agent progress and update job status."""
        last_progress = 20.0  # Starting progress after agent creation

        while True:
            try:
                # Get agent progress (this would need to be implemented in BaseAgent)
                if hasattr(agent, 'get_progress'):
                    progress_info = agent.get_progress()

                    current_progress = min(85.0, last_progress + 5.0)  # Cap at 85% during execution

                    phase = JobPhase.RESEARCHING
                    if progress_info.get("current_step", "").lower().find("analyz") != -1:
                        phase = JobPhase.ANALYZING
                    elif progress_info.get("current_step", "").lower().find("generat") != -1:
                        phase = JobPhase.GENERATING

                    await self.lifecycle_manager.update_job_phase(
                        job_id,
                        phase,
                        current_progress,
                        progress_info.get("current_step", "Processing research"),
                        sources_found=progress_info.get("sources_found", 0)
                    )

                    last_progress = current_progress

                await asyncio.sleep(5)  # Update every 5 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error monitoring agent progress: {e}")
                await asyncio.sleep(10)

    async def _calculate_metrics(
        self,
        agent: BaseAgent,
        execution_time
    ) -> ExecutionMetrics:
        """Calculate execution metrics from agent execution."""
        # This would need to be implemented based on actual agent capabilities
        # For now, return basic metrics

        return ExecutionMetrics(
            total_duration_seconds=execution_time.total_seconds(),
            api_calls_made=getattr(agent, '_api_calls_made', 0),
            tokens_consumed=getattr(agent, '_tokens_consumed', 0),
            estimated_cost_usd=0.0,  # TODO: Calculate based on actual usage
            search_operations=getattr(agent, '_search_operations', 0),
            retry_operations=getattr(agent, '_retry_operations', 0),
            peak_memory_mb=0,  # TODO: Implement memory tracking
            performance_metrics={
                "avg_response_time": 0.0,
                "success_rate": 1.0,
                "error_count": 0
            },
            cost_breakdown={
                "llm_costs": 0.0,
                "search_costs": 0.0,
                "other_costs": 0.0
            }
        )

    async def _extract_sources(self, agent: BaseAgent) -> List[ResearchSource]:
        """Extract research sources from agent execution."""
        sources = []

        # This would need to be implemented based on actual agent source tracking
        if hasattr(agent, 'get_sources'):
            agent_sources = agent.get_sources()

            for i, source in enumerate(agent_sources, 1):
                research_source = ResearchSource(
                    number=i,
                    url=source.get("url", ""),
                    title=source.get("title", ""),
                    content_excerpt=source.get("excerpt", "")[:500],  # Limit excerpt length
                    confidence_score=source.get("confidence", 0.8),
                    discovered_at=source.get("discovered_at", datetime.utcnow()),
                    source_type="web",  # Default type
                    status="processed"  # Default status
                )
                sources.append(research_source)

        return sources


class AgentIntegrationService:
    """Service for managing agent integration with job system."""

    def __init__(self, lifecycle_manager: JobLifecycleManager):
        self.lifecycle_manager = lifecycle_manager
        self.executor = AgentJobExecutor(lifecycle_manager)
        self.active_agents: Dict[str, BaseAgent] = {}

    async def execute_job(self, request: JobRequest) -> JobResult:
        """Execute a job using the agent integration service."""
        try:
            # Store agent reference for potential cancellation
            # (This would be set during agent creation in executor)

            result = await self.executor.execute_job(request)

            # Clean up agent reference
            if request.job_id in self.active_agents:
                del self.active_agents[request.job_id]

            return result

        except Exception as e:
            # Clean up on failure
            if request.job_id in self.active_agents:
                del self.active_agents[request.job_id]
            raise

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job by stopping its agent."""
        if job_id in self.active_agents:
            agent = self.active_agents[job_id]

            # Stop agent execution (this would need to be implemented in BaseAgent)
            if hasattr(agent, 'cancel'):
                await agent.cancel()

            del self.active_agents[job_id]
            logger.info(f"Cancelled agent execution for job {job_id}")
            return True

        return False

    async def get_agent_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of agent executing a job."""
        if job_id in self.active_agents:
            agent = self.active_agents[job_id]

            return {
                "agent_type": type(agent).__name__,
                "state": getattr(agent, 'state', 'unknown'),
                "progress": getattr(agent, 'progress', 0.0),
                "current_step": getattr(agent, 'current_step', ''),
                "sources_found": len(getattr(agent, 'sources', [])),
                "execution_time": (
                    datetime.utcnow() - getattr(agent, 'start_time', datetime.utcnow())
                ).total_seconds()
            }

        return None