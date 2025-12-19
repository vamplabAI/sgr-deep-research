import asyncio
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from sgr_agent_core import AgentFactory, AgentStatesEnum, BaseAgent
from sgr_deep_research.api.models import (
    AgentListItem,
    AgentListResponse,
    AgentStateResponse,
    ChatCompletionRequest,
    ClarificationRequest,
    HealthResponse,
)

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
    """Get a list of available agent models with metadata for OpenWebUI."""
    models_data = []
    
    for agent_def in AgentFactory.get_definitions_list():
        model_info = {
            "id": agent_def.name,
            "object": "model",
            "created": 1234567890,
            "owned_by": "sgr-agent-core",
        }
        
        # Add OpenWebUI metadata if available
        if hasattr(agent_def, "display_name") and agent_def.display_name:
            model_info["name"] = agent_def.display_name
        
        if hasattr(agent_def, "description") and agent_def.description:
            model_info["description"] = agent_def.description
        
        if hasattr(agent_def, "tags") and agent_def.tags:
            model_info["meta"] = {
                "tags": agent_def.tags
            }
        
        models_data.append(model_info)

    return {"data": models_data, "object": "list"}


def extract_user_content_from_messages(messages):
    """Extract last user message content."""
    for message in reversed(messages):
        if message.role == "user":
            return message.content
    raise ValueError("User message not found in messages")


def extract_conversation_history(messages):
    """
    Извлекаем историю диалога, оставляя только финальные ответы ассистента.
    
    Функция фильтрует промежуточные вызовы инструментов, блоки reasoning и HTML details
    из сообщений ассистента, сохраняя только финальный ответ (текст после последнего </details>).
    Это значительно уменьшает размер контекста, сохраняя непрерывность диалога.
    
    Args:
        messages: Список сообщений из запроса
        
    Returns:
        list: Отфильтрованная история диалога с парами user-assistant
    """
    import re
    
    logger.info("🔍 [HISTORY] Starting conversation history extraction")
    logger.info(f"🔍 [HISTORY] Total messages to process: {len(messages)}")
    
    history = []
    
    # Обрабатываем сообщения последовательно, собирая пары user-assistant
    i = 0
    while i < len(messages):
        msg = messages[i]
        
        # Обрабатываем сообщение пользователя
        if msg.role == "user":
            logger.info(f"🔍 [HISTORY] [{i}] Found USER message: {msg.content[:100]}...")
            history.append({
                "role": "user",
                "content": msg.content
            })
            
            # Ищем ответ ассистента (пропускаем tool_calls и tool сообщения)
            assistant_content = None
            j = i + 1
            logger.info(f"🔍 [HISTORY] Looking ahead for assistant response starting from index {j}")
            
            while j < len(messages):
                next_msg = messages[j]
                logger.info(f"🔍 [HISTORY]   [{j}] Checking message: role={next_msg.role}, has_content={bool(next_msg.content)}, content_length={len(next_msg.content) if next_msg.content else 0}")
                
                # Останавливаемся на следующем сообщении пользователя
                if next_msg.role == "user":
                    logger.info(f"🔍 [HISTORY]   [{j}] Hit next user message, stopping search")
                    break
                
                # Собираем контент ассистента (пропускаем tool_calls и tool сообщения)
                if next_msg.role == "assistant" and next_msg.content:
                    logger.info(f"🔍 [HISTORY] [{j}] Found ASSISTANT message, length: {len(next_msg.content)} chars")
                    logger.info(f"🔍 [HISTORY] First 200 chars: {next_msg.content[:200]}...")
                    
                    # Пытаемся извлечь финальный ответ используя несколько стратегий
                    final_answer = None
                    content = next_msg.content
                    
                    # Стратегия 1: Ищем маркер ✓ (маркер финального ответа)
                    checkmark_pos = content.rfind('✓')
                    if checkmark_pos != -1:
                        # Извлекаем всё после маркера ✓
                        final_answer = content[checkmark_pos + 1:].strip()
                        logger.info(f"🔍 [HISTORY] Strategy 1 (✓ marker): Found at pos {checkmark_pos}, extracted {len(final_answer)} chars")
                    
                    # Стратегия 2: Ищем тег </details> и извлекаем текст после него
                    if not final_answer:
                        last_details_end = content.rfind('</details>')
                        if last_details_end != -1:
                            logger.info(f"🔍 [HISTORY] Strategy 2 (</details>): Found at pos {last_details_end}")
                            # Нашли теги details - извлекаем всё после последнего
                            potential_answer = content[last_details_end + len('</details>'):].strip()
                            logger.info(f"🔍 [HISTORY] Text after </details>: {potential_answer[:200]}...")
                            
                            # Очищаем и проверяем, что это значимый контент
                            potential_answer = re.sub(r'^"undefined"\s*', '', potential_answer)
                            potential_answer = re.sub(r'"undefined"', '', potential_answer)
                            potential_answer = re.sub(r'^["\s&quot;]+', '', potential_answer)
                            
                            if len(potential_answer) > 20:  # Только если есть существенный контент
                                final_answer = potential_answer
                                logger.info(f"🔍 [HISTORY] Strategy 2: Extracted {len(final_answer)} chars after cleanup")
                            else:
                                logger.info(f"🔍 [HISTORY] Strategy 2: Skipped (too short after cleanup: {len(potential_answer)} chars)")
                    
                    # Стратегия 3: Если сообщение короткое и без тегов details, используем как есть
                    if not final_answer and len(content) < 500 and '<details' not in content:
                        final_answer = content
                        logger.info(f"🔍 [HISTORY] Strategy 3 (short message): Using as-is, {len(final_answer)} chars")
                    
                    # Стратегия 4: Для длинных сообщений ищем финальный ответ по маркерам
                    # (может содержать reasoning + финальный ответ с markdown заголовками)
                    if not final_answer and len(content) > 5000:
                        logger.info(f"🔍 [HISTORY] Strategy 4: Analyzing long message ({len(content)} chars) for final answer")
                        
                        # Ищем последний блок с markdown заголовком (##) - обычно это финальный ответ
                        # Паттерн: ищем последний заголовок второго уровня
                        markdown_headers = list(re.finditer(r'^##\s+[^\n]+', content, re.MULTILINE))
                        if markdown_headers:
                            # Берем позицию последнего заголовка
                            last_header_pos = markdown_headers[-1].start()
                            potential_answer = content[last_header_pos:].strip()
                            logger.info(f"🔍 [HISTORY] Strategy 4: Found markdown header at pos {last_header_pos}, extracted {len(potential_answer)} chars")
                            
                            # Проверяем, что это не просто заголовок, а есть контент
                            if len(potential_answer) > 100:
                                final_answer = potential_answer
                                logger.info(f"🔍 [HISTORY] Strategy 4: Using content after last markdown header")
                            else:
                                logger.info(f"🔍 [HISTORY] Strategy 4: Content too short ({len(potential_answer)} chars)")
                        else:
                            logger.info(f"🔍 [HISTORY] Strategy 4: No markdown headers found, skipping long message")
                    
                    # Стратегия 5: Если всё ещё нет ответа и сообщение очень длинное, пропускаем
                    # (вероятно содержит только детали выполнения инструментов без финального ответа)
                    if not final_answer and len(content) > 5000:
                        logger.info(f"🔍 [HISTORY] Strategy 5: Skipping long message without final answer ({len(content)} chars)")
                        pass
                    
                    # Очищаем финальный ответ
                    if final_answer:
                        # Убираем HTML entities
                        import html
                        final_answer = html.unescape(final_answer)
                        
                        # Удаляем лишние кавычки и пробелы
                        final_answer = re.sub(r'^["\s]+|["\s]+$', '', final_answer)
                        final_answer = final_answer.strip()
                        
                        if final_answer and len(final_answer) > 10:  # Сохраняем только если значимый
                            assistant_content = final_answer
                            logger.info(f"🔍 [HISTORY] ✅ Final answer extracted: {final_answer[:150]}...")
                        else:
                            logger.info(f"🔍 [HISTORY] ❌ Final answer too short after cleanup: {len(final_answer)} chars")
                    else:
                        logger.info(f"🔍 [HISTORY] ❌ No final answer extracted from assistant message")
                
                j += 1
            
            # Добавляем ответ ассистента, если найден
            if assistant_content:
                logger.info(f"🔍 [HISTORY] ✅ Adding assistant response to history: {assistant_content[:100]}...")
                history.append({
                    "role": "assistant",
                    "content": assistant_content
                })
            else:
                logger.info(f"🔍 [HISTORY] ⚠️  No assistant response found for user message at index {i}")
            
            # ИСПРАВЛЕНИЕ: Переходим к следующему сообщению после обработанного блока
            # j уже указывает на следующее необработанное сообщение (user или конец)
            logger.info(f"🔍 [HISTORY] Moving to next turn, new i={j}")
            i = j
        else:
            # Пропускаем не-user сообщения в начале
            logger.info(f"🔍 [HISTORY] [{i}] Skipping non-user message at start: role={msg.role}")
            i += 1
    
    logger.info(f"🔍 [HISTORY] ✅ Extraction complete: {len(history)} messages in history")
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
    """Check if the model string is an agent ID (contains underscore and UUID-
    like format)."""
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
        
        # Инжектим историю диалога в агента ПЕРЕД выполнением, чтобы сохранить контекст беседы
        if len(conversation_history) > 0:
            # Проверяем, есть ли в истории последнее сообщение пользователя с текущим task
            if (conversation_history[-1]["role"] == "user" and 
                conversation_history[-1]["content"].strip() == task.strip()):
                # Последнее сообщение совпадает с текущим task - используем всю историю как есть
                # Task НЕ будет добавлен в _prepare_context(), так как уже есть в истории
                logger.info(f"📜 Injecting {len(conversation_history)} historical messages into agent conversation (including current task)")
                agent.conversation.extend(conversation_history)
                
                # Переопределяем _prepare_context(), чтобы НЕ добавлять task дважды
                # Сохраняем оригинальный метод для использования промптов
                from sgr_agent_core.services.prompt_loader import PromptLoader
                original_prepare_context = agent._prepare_context
                
                async def _prepare_context_with_history():
                    """Подготавливаем контекст БЕЗ добавления task, так как он уже в истории."""
                    return [
                        {"role": "system", "content": PromptLoader.get_system_prompt(agent.toolkit, agent.config.prompts)},
                        *agent.conversation,  # История уже содержит текущий task
                    ]
                
                agent._prepare_context = _prepare_context_with_history
            else:
                # Последнее сообщение НЕ совпадает с текущим task
                # Добавляем историю БЕЗ текущего task - он будет добавлен в _prepare_context()
                logger.info(f"📜 Injecting {len(conversation_history)} historical messages into agent conversation (task will be added separately)")
                agent.conversation.extend(conversation_history)
        
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
