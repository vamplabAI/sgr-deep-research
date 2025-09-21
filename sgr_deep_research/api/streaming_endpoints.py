"""SSE streaming endpoints for job updates."""

import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from sgr_deep_research.core.job_storage import JobStorage
from sgr_deep_research.core.job_queue_manager import JobQueueManager

logger = logging.getLogger(__name__)

# Initialize job services
job_storage = JobStorage()
job_queue_manager = JobQueueManager()

app = FastAPI()


async def job_event_generator(job_id: str) -> AsyncGenerator[str, None]:
    """Generate SSE events for job updates."""
    try:
        # Check if job exists
        job_status = await job_storage.get_job_status(job_id)
        if not job_status:
            yield f"event: error\ndata: {{\"error\": \"Job not found\"}}\n\n"
            return

        # Send initial status
        yield f"event: job_status\ndata: {json.dumps({
            'job_id': job_id,
            'status': job_status.status.value,
            'progress': job_status.progress
        })}\n\n"

        # Monitor job progress
        while True:
            current_status = await job_storage.get_job_status(job_id)
            if not current_status:
                break

            # Send progress update
            event_data = {
                "job_id": job_id,
                "status": current_status.status.value,
                "progress": current_status.progress,
                "current_step": current_status.current_step,
                "steps_completed": current_status.steps_completed,
                "total_steps": current_status.total_steps
            }

            yield f"event: job_progress\ndata: {json.dumps(event_data)}\n\n"

            # Check if job is complete
            if current_status.status.value in ["completed", "failed", "cancelled"]:
                yield f"event: job_complete\ndata: {json.dumps({
                    'job_id': job_id,
                    'status': current_status.status.value
                })}\n\n"
                break

            # Wait before next update
            await asyncio.sleep(2)

    except Exception as e:
        logger.error(f"Error in job event generator for {job_id}: {e}")
        yield f"event: error\ndata: {{\"error\": \"Internal server error\"}}\n\n"


@app.get("/jobs/{job_id}/stream")
async def stream_job_updates(job_id: str):
    """Stream job progress updates via Server-Sent Events."""
    try:
        return StreamingResponse(
            job_event_generator(job_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
    except Exception as e:
        logger.error(f"Error setting up stream for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))