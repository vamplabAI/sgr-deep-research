"""Утилиты для конвертации Pydantic-моделей в формат OpenAI function calling.

Модуль предоставляет функции для автоматического преобразования Pydantic-моделей
в JSON Schema, совместимый с OpenAI Function Calling API.
"""

from typing import Any, Dict, Type, get_origin, get_args, Union, Literal, Annotated

from pydantic import BaseModel
from pydantic.fields import FieldInfo


def pydantic_to_tools(
    model: Type[BaseModel],
    name: str = None,
    description: str = None
) -> list:
    """Конвертирует Pydantic модель в формат OpenAI function calling tool.
    
    Args:
        model: Pydantic модель для конвертации
        name: Имя функции (по умолчанию используется имя класса)
        description: Описание функции (по умолчанию используется docstring класса)
    
    Returns:
        Список с одним элементом в формате OpenAI tools
    """
    return [{
        "type": "function",
        "function": {
            "name": name or model.__name__,
            "description": description or model.__doc__ or f"Function {model.__name__}",
            "parameters": pydantic_to_json_schema(model)
        }
    }]


def pydantic_to_json_schema(model: Type[BaseModel]) -> Dict[str, Any]:
    """Конвертирует Pydantic модель в JSON Schema для OpenAI.
    
    Args:
        model: Pydantic модель
    
    Returns:
        JSON Schema словарь
    """
    properties = {}
    required = []
    
    for field_name, field_info in model.model_fields.items():
        field_schema = _field_to_json_schema(field_info, field_name)
        properties[field_name] = field_schema
        
        # Проверим обязательность поля
        if field_info.is_required():
            required.append(field_name)
    
    schema = {
        "type": "object",
        "properties": properties
    }
    
    if required:
        schema["required"] = required
    
    return schema


def _field_to_json_schema(field_info: FieldInfo, field_name: str) -> Dict[str, Any]:
    """Конвертирует поле Pydantic в JSON Schema.
    
    Args:
        field_info: Информация о поле
        field_name: Имя поля
    
    Returns:
        JSON Schema для поля
    """
    field_type = field_info.annotation
    schema = {}
    
    # Добавляем описание если есть
    if field_info.description:
        schema["description"] = field_info.description
    
    # Обрабатываем тип поля
    schema.update(_type_to_json_schema(field_type))
    
    # Извлекаем constraints из metadata (для Annotated типов)
    if hasattr(field_info, 'metadata') and field_info.metadata:
        for constraint in field_info.metadata:
            if hasattr(constraint, 'ge'):  # greater or equal
                schema["minimum"] = constraint.ge
            if hasattr(constraint, 'le'):  # less or equal
                schema["maximum"] = constraint.le
            if hasattr(constraint, 'gt'):  # greater than
                schema["exclusiveMinimum"] = constraint.gt
            if hasattr(constraint, 'lt'):  # less than
                schema["exclusiveMaximum"] = constraint.lt
            if hasattr(constraint, 'min_length'):
                schema["minLength"] = constraint.min_length
            if hasattr(constraint, 'max_length'):
                schema["maxLength"] = constraint.max_length
            if hasattr(constraint, 'pattern'):
                schema["pattern"] = constraint.pattern
    
    # Добавляем default если есть и поле не required
    if field_info.default is not None and not field_info.is_required():
        schema["default"] = field_info.default
    
    # Добавляем примеры если есть
    if hasattr(field_info, 'examples') and field_info.examples:
        schema["examples"] = field_info.examples
    
    return schema


def _type_to_json_schema(python_type: Any) -> Dict[str, Any]:
    """Конвертирует Python тип в JSON Schema тип.
    
    Args:
        python_type: Python тип
    
    Returns:
        JSON Schema тип
    """
    origin = get_origin(python_type)
    
    # Обработка Literal["a", "b", "c"]
    if origin is Literal:
        args = get_args(python_type)
        # Определяем тип из первого значения
        if args:
            first_val = args[0]
            if isinstance(first_val, str):
                base_type = "string"
            elif isinstance(first_val, int):
                base_type = "integer"
            elif isinstance(first_val, bool):
                base_type = "boolean"
            else:
                base_type = "string"
            
            return {
                "type": base_type,
                "enum": list(args)
            }
        return {"type": "string"}
    
    # Обработка Annotated[T, ...]
    if origin is Annotated:
        args = get_args(python_type)
        # Первый аргумент - это сам тип
        return _type_to_json_schema(args[0])
    
    # Обработка Optional[T] и Union[T, None]
    if origin is Union:
        args = get_args(python_type)
        # Фильтруем None из Union
        non_none_args = [arg for arg in args if arg is not type(None)]
        
        if len(non_none_args) == 1:
            # Optional[T] случай
            return _type_to_json_schema(non_none_args[0])
        else:
            # Множественный Union - используем anyOf
            return {
                "anyOf": [_type_to_json_schema(arg) for arg in non_none_args]
            }
    
    # Обработка List[T]
    if origin is list:
        args = get_args(python_type)
        item_schema = _type_to_json_schema(args[0]) if args else {"type": "string"}
        return {
            "type": "array",
            "items": item_schema
        }
    
    # Обработка Dict[K, V]
    if origin is dict:
        args = get_args(python_type)
        value_schema = _type_to_json_schema(args[1]) if len(args) > 1 else {}
        return {
            "type": "object",
            "additionalProperties": value_schema if value_schema else True
        }
    
    # Обработка вложенных Pydantic моделей
    if isinstance(python_type, type) and issubclass(python_type, BaseModel):
        return pydantic_to_json_schema(python_type)
    
    # Базовые типы
    type_mapping = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        type(None): {"type": "null"}
    }
    
    return type_mapping.get(python_type, {"type": "string"})
