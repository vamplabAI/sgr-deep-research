import asyncio
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from sgr_deep_research.api.models import (
    AgentListItem,
    AgentListResponse,
    AgentStateResponse,
    ChatCompletionRequest,
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
    """Get list of available agent models."""
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


def extract_user_content_from_messages(messages):
    """Extract last user message content."""
    for message in reversed(messages):
        if message.role == "user":
            return message.content
    raise ValueError("User message not found in messages")


def extract_conversation_history(messages):
    """Extract conversation history with only final answers from assistant.
    
    This function filters out intermediate tool calls, reasoning blocks, and HTML details
    from assistant messages, keeping only the final answer (text after last </details> tag).
    This significantly reduces context size while preserving conversation continuity.
    """
    import re
    
    history = []
    for msg in messages:
        if msg.role == "user":
            history.append({
                "role": msg.role,
                "content": msg.content
            })
        elif msg.role == "assistant" and msg.content:
            # Extract text after the last </details> tag (the final answer)
            # This removes all reasoning and tool execution details
            last_details_end = msg.content.rfind('</details>')
            
            if last_details_end != -1:
                # Found details tags - extract everything after the last one
                final_answer = msg.content[last_details_end + len('</details>'):].strip()
                
                if final_answer:
                    history.append({
                        "role": msg.role,
                        "content": final_answer
                    })
            else:
                # No details tags found - use message as-is if short
                # This handles edge cases where message doesn't have our format
                if len(msg.content) < 500:  # Short messages likely don't have tool calls
                    history.append({
                        "role": msg.role,
                        "content": msg.content
                    })
    
    return history


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
    """Check if model string is an agent ID (contains underscore and UUID-like
    format)."""
    return "_" in model_str and len(model_str) > 20


@router.post("/v1/chat/completions")
async def create_chat_completion(request: ChatCompletionRequest):
    # Log full payload for debugging
    logger.info("=" * 80)
    logger.info("📥 INCOMING REQUEST PAYLOAD:")
    logger.info(f"Model: {request.model}")
    logger.info(f"Stream: {request.stream}")
    logger.info(f"Messages count: {len(request.messages)}")
    logger.info("Messages:")
    for i, msg in enumerate(request.messages):
        logger.info(f"  [{i}] Role: {msg.role}, Content: {msg.content[:20000] if msg.content else 'None'}...")
    logger.info("=" * 80)
    
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
        logger.info(f"🔄 Detected clarification request for existing agent: {request.model}")
        return await provide_clarification(
            agent_id=request.model,
            request=ClarificationRequest(clarifications=extract_user_content_from_messages(request.messages)),
        )

    try:
        task = extract_user_content_from_messages(request.messages)
        
        # Calculate original size before filtering
        original_size = sum(len(msg.content or "") for msg in request.messages if msg.role == "assistant")
        
        conversation_history = extract_conversation_history(request.messages)
        
        # Calculate filtered size
        filtered_size = sum(len(msg["content"]) for msg in conversation_history if msg["role"] == "assistant")
        
        logger.info(f"📝 Extracted task: {task[:200]}...")
        logger.info(f"📚 Conversation history: {len(conversation_history)} messages")
        if original_size > 0:
            reduction_pct = ((original_size - filtered_size) / original_size) * 100
            logger.info(f"💾 Context size reduction: {original_size} → {filtered_size} chars ({reduction_pct:.1f}% saved)")
        
        if len(conversation_history) > 1:
            logger.info("💬 Filtered conversation history (final answers only):")
            for i, msg in enumerate(conversation_history):
                logger.info(f"  [{i}] {msg['role']}: {msg['content'][:150]}...")

        agent_def = next(filter(lambda ad: ad.name == request.model, AgentFactory.get_definitions_list()), None)
        if not agent_def:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model '{request.model}'. "
                f"Available models: {[ad.name for ad in AgentFactory.get_definitions_list()]}",
            )
        agent = await AgentFactory.create(agent_def, task)
        
        # Inject conversation history into agent BEFORE execution
        if len(conversation_history) > 1:
            # Remove the last user message (it's the current task, will be added by execute())
            history_without_current = conversation_history[:-1]
            logger.info(f"📜 Injecting {len(history_without_current)} historical messages into agent conversation")
            agent.conversation.extend(history_without_current)
        
        logger.info(f"✅ Created agent '{request.model}' for task: {task[:100]}...")

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
