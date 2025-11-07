"""Адаптер для работы с qwen3-thinking моделями через Function Calling.

Thinking модели семейства qwen3 не поддерживают напрямую Structured Output (SO),
но могут работать через Function Calling (FC). Этот адаптер извлекает структурированные
данные из ответов thinking-моделей, которые содержат промежуточные рассуждения вместе
с результатами вызова инструментов.
"""

import json
import logging
import re
from typing import Optional, Type

from pydantic import BaseModel

logger = logging.getLogger(__name__)


def robust_json_extract(text: str) -> list[dict]:
    """Извлекает все возможные JSON-объекты из 'грязного' текста.
    
    Args:
        text: Текст, содержащий JSON-объекты
        
    Returns:
        Список извлеченных JSON-объектов
    """
    if not text or not text.strip():
        return []

    results = []
    seen = set()

    # 1. Markdown-блоки ```json ... ```
    json_blocks = re.findall(r"```(?:json)?\s*({.*?})\s*```", text, re.DOTALL | re.IGNORECASE)
    candidates = json_blocks[:]

    # 2. Все {...} конструкции (нежадно и жадно)
    candidates += re.findall(r"\{.*?\}", text, re.DOTALL)
    candidates += re.findall(r"\{.*\}", text, re.DOTALL)

    # Убираем дубли, сортируем по длине (длиннее — раньше)
    unique = []
    for c in candidates:
        c_clean = c.strip()
        if c_clean and c_clean not in seen:
            seen.add(c_clean)
            unique.append(c_clean)
    unique.sort(key=len, reverse=True)

    for cand in unique:
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict):
                results.append(obj)
        except (json.JSONDecodeError, ValueError):
            continue
    return results


def extract_tool_call_from_tags(text: str) -> Optional[dict]:
    """Извлекает JSON из тегов <tool_call>...</tool_call>.
    
    Args:
        text: Текст, содержащий теги tool_call
        
    Returns:
        Извлеченный JSON-объект или None
    """
    pattern = r'<tool_call>\s*(\{.*?\})\s*</tool_call>'
    matches = re.findall(pattern, text, re.DOTALL)
    if not matches:
        return None
    
    # Берём последний (самый актуальный) tool_call
    for match in reversed(matches):
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    return None


def extract_structured_response(
    response_message: dict,
    schema_class: Type[BaseModel],
    tool_name: str
) -> BaseModel:
    """Извлекает структурированный ответ из ответа thinking-модели.
    
    Thinking модели могут возвращать данные в разных форматах:
    1. В поле tool_calls[].function.arguments (чистый JSON или с рассуждениями)
    2. В поле content с тегами <tool_call>...</tool_call>
    3. В поле content как чистый JSON
    
    Args:
        response_message: Сообщение от API (choices[0].message)
        schema_class: Pydantic-класс для валидации ответа
        tool_name: Имя инструмента
        
    Returns:
        Валидированный объект Pydantic-модели
        
    Raises:
        RuntimeError: Если не удалось извлечь или валидировать ответ
    """
    content = (response_message.get('content') or '').strip()
    tool_calls = response_message.get('tool_calls') or []
    
    validation_errors = []

    # === Стратегия 1: tool_calls с чистым JSON в arguments ===
    for tc in tool_calls:
        if tc.get('type') != 'function':
            continue
        
        func = tc.get('function', {})
        name = func.get('name')
        if name != tool_name:
            continue
        
        raw_args = func.get('arguments', '')
        if not raw_args:
            continue
        
        # Парсим arguments
        if isinstance(raw_args, str):
            # Сначала пробуем как чистый JSON
            try:
                args = json.loads(raw_args)
                validated = schema_class.model_validate(args)
                logger.debug(f"Успешно извлечен ответ из tool_calls.arguments (JSON)")
                return validated
            except json.JSONDecodeError:
                # Может быть рассуждения + JSON, извлекаем все JSON-объекты
                json_objects = robust_json_extract(raw_args)
                for obj in json_objects:
                    try:
                        validated = schema_class.model_validate(obj)
                        logger.debug(f"Успешно извлечен ответ из tool_calls.arguments (extracted JSON)")
                        return validated
                    except (ValueError, TypeError) as e:
                        validation_errors.append(f"tool_calls.arguments JSON: {type(e).__name__}: {e}")
            except (ValueError, TypeError) as e:
                validation_errors.append(f"tool_calls.arguments: {type(e).__name__}: {e}")
        elif isinstance(raw_args, dict):
            try:
                validated = schema_class.model_validate(raw_args)
                logger.debug(f"Успешно извлечен ответ из tool_calls.arguments (dict)")
                return validated
            except (ValueError, TypeError) as e:
                validation_errors.append(f"tool_calls.arguments dict: {type(e).__name__}: {e}")

    # === Стратегия 2: content с тегами <tool_call>...</tool_call> (ПРИОРИТЕТ!) ===
    if content:
        tool_call_obj = extract_tool_call_from_tags(content)
        if tool_call_obj:
            # Случай 1: {"name": "...", "arguments": {...}}
            if tool_call_obj.get('name') == tool_name and 'arguments' in tool_call_obj:
                args = tool_call_obj['arguments']
                try:
                    validated = schema_class.model_validate(args)
                    logger.debug(f"Успешно извлечен ответ из <tool_call> с name")
                    return validated
                except (ValueError, TypeError) as e:
                    validation_errors.append(f"<tool_call> with name: {type(e).__name__}: {e}")
            
            # Случай 2: прямой JSON без обёртки {"name": ...}
            try:
                validated = schema_class.model_validate(tool_call_obj)
                logger.debug(f"Успешно извлечен ответ из <tool_call> прямой JSON")
                return validated
            except (ValueError, TypeError) as e:
                validation_errors.append(f"<tool_call> direct: {type(e).__name__}: {e}")

    # === Стратегия 3: content с чистым JSON ===
    if content:
        json_objects = robust_json_extract(content)
        for obj in json_objects:
            try:
                validated = schema_class.model_validate(obj)
                logger.debug(f"Успешно извлечен ответ из content JSON")
                return validated
            except (ValueError, TypeError) as e:
                validation_errors.append(f"content JSON object: {type(e).__name__}: {e}")

    # === Ничего не сработало ===
    error_details = [
        f"Не удалось извлечь структурированный ответ для {tool_name}",
        f"Content length: {len(content)}",
        f"Content preview: {content[:300]!r}",
        f"Tool calls count: {len(tool_calls)}",
        f"Tool calls: {tool_calls!r}",
        f"Validation attempts: {len(validation_errors)}",
    ]
    if validation_errors:
        error_details.append("Validation errors:")
        error_details.extend(f"  - {err}" for err in validation_errors[:5])
    
    raise RuntimeError("\n".join(error_details))
