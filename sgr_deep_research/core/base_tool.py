from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, ClassVar

from fastmcp import Client
from pydantic import BaseModel

# from sgr_deep_research.core.models import AgentStatesEnum
from sgr_deep_research.settings import get_config

if TYPE_CHECKING:
    from sgr_deep_research.core.models import ResearchContext

config = get_config()
logger = logging.getLogger(__name__)


class BaseTool(BaseModel):
    """Class to provide tool handling capabilities."""

    tool_name: ClassVar[str] = None
    description: ClassVar[str] = None

    @classmethod
    def schema_to_instruction(
            cls,
            prefix: str = "",
            suffix: str = "",
            include_required: bool = True,
            include_constraints: bool = True,
            include_defaults: bool = False,  # Новый параметр для значений по умолчанию
            enum_limit: int = 6,
            max_depth: int = 2,  # Защита от бесконечной рекурсии для вложенных объектов
    ) -> str:
        """Build a concise, human-readable instruction from the model JSON Schema.

        Args:
            cls: Pydantic model class
            prefix: Instruction prefix
            suffix: Instruction suffix
            include_required: Whether to mark required fields
            include_constraints: Whether to include type and validation constraints
            include_defaults: Whether to show default values
            enum_limit: Maximum enum values to show
            max_depth: Maximum recursion depth for nested objects
        """

        def process_schema(
                schema: dict,
                current_depth: int = 0,
                definitions: dict = None
        ) -> list[str]:
            if current_depth > max_depth:
                return ["object{...}"]

            definitions = definitions or schema.get("$defs", {})
            properties = schema.get("properties", {})
            required_fields = set(schema.get("required", []) or [])

            parts: list[str] = []

            def resolve_ref(ref: str) -> dict:
                """Resolve $ref references to definitions"""
                if ref.startswith("#/$defs/"):
                    def_name = ref.split("/")[-1]
                    return definitions.get(def_name, {})
                return {}

            def summarize_type(meta: dict) -> str | None:
                """Extract and format type information"""
                # Обработка $ref
                if "$ref" in meta:
                    ref_schema = resolve_ref(meta["$ref"])
                    if ref_schema.get("type") == "object":
                        return "object"
                    return summarize_type(ref_schema)

                t = meta.get("type")

                # Обработка массивов
                if t == "array":
                    items = meta.get("items", {})
                    if "$ref" in items:
                        ref_schema = resolve_ref(items["$ref"])
                        item_type = ref_schema.get("type", "object")
                    else:
                        item_type = items.get("type")
                        if not item_type:
                            # Обработка anyOf/oneOf для сложных типов
                            for key in ["anyOf", "oneOf"]:
                                if key in items:
                                    types = [i.get("type", "unknown") for i in items[key] if isinstance(i, dict)]
                                    if types:
                                        item_type = "/".join(sorted(set(types)))
                                        break
                    return f"array[{item_type or 'any'}]"

                # Обработка вложенных объектов
                if t == "object":
                    nested_props = meta.get("properties")
                    if nested_props:
                        nested_parts = process_schema(meta, current_depth + 1, definitions)
                        return f"object{{{', '.join(nested_parts)}}}"
                    return "object"

                # Обработка составных типов
                if not t:
                    for key in ["anyOf", "oneOf", "allOf"]:
                        if key in meta:
                            types = []
                            for item in meta[key]:
                                if "$ref" in item:
                                    ref_schema = resolve_ref(item["$ref"])
                                    types.append(ref_schema.get("type", "object"))
                                else:
                                    types.append(item.get("type", "unknown"))
                            if types:
                                return "/".join(sorted(set(types)))
                return t

            for name, meta in properties.items():
                # Обработка ссылок
                if "$ref" in meta:
                    meta = {**resolve_ref(meta["$ref"]), **meta}

                desc = meta.get("description", "").strip()
                constraints: list[str] = []

                if include_constraints:
                    t = summarize_type(meta)
                    if t:
                        constraints.append(t)

                    # Числовые ограничения
                    for constraint in ["minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum"]:
                        if constraint in meta:
                            constraints.append(f"{constraint}={meta[constraint]}")

                    # Строковые/массив ограничения
                    if (ml := meta.get("minLength")) is not None:
                        constraints.append(f"minLength={ml}")
                    if (mx := meta.get("maxLength")) is not None:
                        constraints.append(f"maxLength={mx}")
                    if (mi := meta.get("minItems")) is not None:
                        constraints.append(f"minItems={mi}")
                    if (ma := meta.get("maxItems")) is not None:
                        constraints.append(f"maxItems={ma}")

                    # Форматы и паттерны
                    if (fmt := meta.get("format")):
                        constraints.append(f"format={fmt}")
                    if (pattern := meta.get("pattern")):
                        # Упрощаем сложные regex для читаемости
                        simple_pattern = pattern.replace("^", "").replace("$", "").replace("\\", "")
                        if len(simple_pattern) <= 20:
                            constraints.append(f"pattern={simple_pattern}")
                        else:
                            constraints.append("pattern=...")

                    # Enum
                    enum_vals = meta.get("enum")
                    if isinstance(enum_vals, list) and enum_vals:
                        if len(enum_vals) <= enum_limit:
                            constraints.append("enum=" + "/".join(map(str, enum_vals)))
                        else:
                            constraints.append(f"enum[{len(enum_vals)}]")

                suffix_bits: list[str] = []

                # Обязательные поля
                if include_required and name in required_fields:
                    suffix_bits.append("required")

                # Значения по умолчанию
                if include_defaults and "default" in meta:
                    default_val = meta["default"]
                    if default_val is None:
                        suffix_bits.append("default=null")
                    elif isinstance(default_val, (str, int, float, bool)):
                        suffix_bits.append(f"default={default_val}")
                    else:
                        suffix_bits.append("default=...")

                # Описание
                if desc:
                    suffix_bits.append(desc)

                # Ограничения
                if constraints:
                    suffix_bits.append(", ".join(constraints))

                rendered_suffix = f" ({'; '.join(suffix_bits)})" if suffix_bits else ""
                parts.append(f"{name}{rendered_suffix}")

            return parts

        schema = cls.model_json_schema()
        parts = process_schema(schema)
        instruction_core = ", ".join(parts)

        return ((prefix + " ") if prefix else "") + instruction_core + ((" " + suffix) if suffix else "")

    async def __call__(self, context: ResearchContext) -> str:
        """Result should be a string or dumped json."""
        raise NotImplementedError("Execute method must be implemented by subclass")

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.tool_name = cls.tool_name or cls.__name__.lower()
        cls.description = cls.description or cls.__doc__ or ""


class MCPBaseTool(BaseTool):
    """Base model for MCP Tool schema."""

    _client: ClassVar[Client | None] = None

    async def __call__(self, _context) -> str:
        payload = self.model_dump()
        try:
            async with self._client:
                result = await self._client.call_tool(self.tool_name, payload)
                return json.dumps([m.model_dump_json() for m in result.content], ensure_ascii=False)[
                    : config.mcp.context_limit
                ]
        except Exception as e:
            logger.error(f"Error processing MCP tool {self.tool_name}: {e}")
            return f"Error: {e}"
