import asyncio
import logging
from typing import Any, Dict, List, Union

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from sgr_deep_research.api.models import (
    AgentListItem,
    AgentListResponse,
    AgentStateResponse,
    ChatCompletionRequest,
    ChatMessage,
    ClarificationRequest,
    HealthResponse,
)
from sgr_deep_research.core import BaseAgent
from sgr_deep_research.core.agent_factory import AgentFactory
from sgr_deep_research.core.models import AgentStatesEnum

logger = logging.getLogger(__name__)

router = APIRouter()

# ToDo: better to move to a separate service
agents_storage: dict[str, BaseAgent] = {}


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse()


@router.get("/agents/{agent_id}/state", response_model=AgentStateResponse)
async def get_agent_state(agent_id: str):
    if agent_id not in agents_storage:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent = agents_storage[agent_id]

    return AgentStateResponse(
        agent_id=agent.id,
        task=agent.task,
        sources_count=len(agent._context.sources),
        **agent._context.model_dump(),
    )


@router.get("/agents", response_model=AgentListResponse)
async def get_agents_list():
    agents_list = [
        AgentListItem(
            agent_id=agent.id,
            task=agent.task,
            state=agent._context.state,
            creation_time=agent.creation_time,
        )
        for agent in agents_storage.values()
    ]

    return AgentListResponse(agents=agents_list, total=len(agents_list))


@router.get("/v1/models")
async def get_available_models():
    """Get a list of available agent models."""
    models_data = [
        {
            "id": agent_def.name,
            "object": "model",
            "created": 1234567890,
            "owned_by": "sgr-deep-research",
        }
        for agent_def in AgentFactory.get_definitions_list()
    ]

    return {"data": models_data, "object": "list"}


def _prepare_message_content(message: ChatMessage) -> Union[str, List[Dict[str, Any]]]:
    """Prepare message content: merge content with images field if present.

    Images are passed as-is (URLs/base64) without any processing.
    Returns content in OpenAI-compatible format (str or list of parts).
    """
    content = message.content

    # If no images field, return content as-is
    if not message.images:
        return content

    # Wrap images in OpenAI image_url format (pass URLs/base64 as-is)
    image_parts = [{"type": "image_url", "image_url": {"url": img, "detail": "auto"}} for img in message.images]

    # Merge with existing content
    if isinstance(content, str):
        # Convert string to parts format
        parts = [{"type": "text", "text": content}] if content else []
        return parts + image_parts
    elif isinstance(content, list):
        # Already in parts format, append images
        return content + image_parts
    else:
        # Fallback: empty content, just images
        return image_parts


def extract_task_from_first_user_message(messages: list[ChatMessage]) -> str:
    """Extract task text from the first user message (for agent initialization
    and logging).

    Returns text content from the first user message, ignoring images.
    Used only for agent.task field and prompt template - actual conversation context
    is passed separately via agent.conversation.
    """
    for message in messages:
        if message.role == "user":
            if isinstance(message.content, str):
                return message.content
            elif isinstance(message.content, list):
                text_parts = [p.get("text") for p in message.content if isinstance(p, dict) and p.get("type") == "text"]
                text = " ".join(filter(None, text_parts))
                if text:
                    return text

    return "Image-only request"


@router.post("/agents/{agent_id}/provide_clarification")
async def provide_clarification(agent_id: str, request: ClarificationRequest):
    try:
        agent = agents_storage.get(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        logger.info(f"Providing clarification to agent {agent.id}: {request.clarifications[:100]}...")

        await agent.provide_clarification(request.clarifications)
        return StreamingResponse(
            agent.streaming_generator.stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Agent-ID": str(agent.id),
            },
        )

    except Exception as e:
        logger.error(f"Error completion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _is_agent_id(model_str: str) -> bool:
    """Check if the model string is an agent ID (contains underscore and UUID-
    like format)."""
    return "_" in model_str and len(model_str) > 20


@router.post("/v1/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest):
    if not request.stream:
        raise HTTPException(status_code=501, detail="Only streaming responses are supported. Set 'stream=true'")

    # Check if this is a clarification request for an existing agent
    if (
        request.model
        and isinstance(request.model, str)
        and _is_agent_id(request.model)
        and request.model in agents_storage
        and agents_storage[request.model]._context.state == AgentStatesEnum.WAITING_FOR_CLARIFICATION
    ):
        return await provide_clarification(
            agent_id=request.model,
            request=ClarificationRequest(clarifications=extract_task_from_first_user_message(request.messages)),
        )

    try:
        # Extract task text from first user message (for logging/prompts only)
        # Full conversation context is passed via agent.conversation
        task = extract_task_from_first_user_message(request.messages)

        # Process all messages: merge images field into content parts
        processed_messages = []
        for msg in request.messages:
            processed_content = _prepare_message_content(msg)
            processed_messages.append({"role": msg.role, "content": processed_content})

        agent_def = next(filter(lambda ad: ad.name == request.model, AgentFactory.get_definitions_list()), None)
        if not agent_def:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model '{request.model}'. "
                f"Available models: {[ad.name for ad in AgentFactory.get_definitions_list()]}",
            )
        agent = await AgentFactory.create(agent_def, task)
        logger.info(f"Created agent '{request.model}' for task: {task[:100]}...")

        # Add all processed messages to agent conversation (excluding system, which is added by _prepare_context)
        for msg in processed_messages:
            if msg["role"] != "system":
                agent.conversation.append(msg)

        agents_storage[agent.id] = agent
        _ = asyncio.create_task(agent.execute())
        return StreamingResponse(
            agent.streaming_generator.stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Agent-ID": str(agent.id),
                "X-Agent-Model": request.model,
            },
        )

    except ValueError as e:
        logger.error(f"Error completion: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
