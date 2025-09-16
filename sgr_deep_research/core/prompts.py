import os
from datetime import datetime
from functools import cache
from typing import Optional

from sgr_deep_research.core.models import SourceData
from sgr_deep_research.core.tools import BaseTool
from sgr_deep_research.settings import get_config

config = get_config()


class PromptLoader:
    _last_resolved_prompt_path: Optional[str] = None

    @classmethod
    @cache
    def _load_prompt_file(cls, filename: str) -> str:
        # Allow absolute/relative direct paths first
        if os.path.isabs(filename) or os.path.sep in filename:
            if os.path.exists(filename):
                try:
                    with open(filename, encoding="utf-8") as f:
                        content = f.read().strip()
                        PromptLoader._last_resolved_prompt_path = filename
                        return content
                except IOError as e:
                    raise IOError(f"Error reading prompt file {filename}: {e}") from e

        user_file_path = os.path.join(config.prompts.prompts_dir, filename)
        lib_file_path = os.path.join(os.path.dirname(__file__), "..", config.prompts.prompts_dir, filename)

        for file_path in [user_file_path, lib_file_path]:
            if os.path.exists(file_path):
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read().strip()
                        PromptLoader._last_resolved_prompt_path = file_path
                        return content
                except IOError as e:
                    raise IOError(f"Error reading prompt file {file_path}: {e}") from e

        raise FileNotFoundError(f"Prompt file not found: {user_file_path} or {lib_file_path}")

    @classmethod
    def get_tool_function_prompt(cls) -> str:
        return cls._load_prompt_file(config.prompts.tool_function_prompt_file)

    @classmethod
    def get_system_prompt(
        cls,
        user_request: str,
        sources: list[SourceData],
        available_tools: list[BaseTool],
        deep_level: int = 0,
        system_prompt_key_or_file: Optional[str] = None,
    ) -> str:
        sources_formatted = "\n".join([str(source) for source in sources])
        available_tools_str_list = [
            f"{i}. {tool.tool_name}: {tool.description}" for i, tool in enumerate(available_tools, start=1)
        ]

        # Resolve which template to use
        template_file: str

        if system_prompt_key_or_file:
            # First try to resolve as a named preset
            template_file = config.prompts.available_prompts.get(system_prompt_key_or_file, system_prompt_key_or_file)
        else:
            # Auto-select: deep preset for deep mode (if available), otherwise default
            if deep_level > 0:
                template_file = config.prompts.available_prompts.get("deep", "extended_system_prompt.txt")
            else:
                template_file = config.prompts.available_prompts.get("default", config.prompts.system_prompt_file)

        # Load template (with fallback to default system prompt)
        try:
            template = cls._load_prompt_file(template_file)
        except FileNotFoundError:
            template = cls._load_prompt_file(config.prompts.system_prompt_file)

        # Добавляем инструкции для глубокого режима
        deep_mode_instructions = ""
        if deep_level > 0:
            min_searches = min(deep_level * 3 + 2, 15)  # 2->5, 3->8, 4->11, 5->14, max 15
            deep_mode_instructions = f"""
DEEP RESEARCH MODE LEVEL {deep_level} ACTIVATED:
- MINIMUM REQUIRED SEARCHES: {min_searches} different search queries before considering data sufficient
- Current searches done: {{searches_count}}/{{max_searches}}
- You MUST perform MULTIPLE diverse search queries covering different aspects of the topic
- Set enough_data=False UNTIL you have conducted at least {min_searches} searches
- Search variations: different keywords, specific terms, related concepts, historical context, recent developments
- For topics like history: search periods, regions, key figures, institutions, sources, conflicts, demographics
- Example search progression: broad overview → specific periods → key events → sources analysis → related peoples/regions
- DEPTH OVER SPEED: More thorough analysis is expected at this deep level
"""

        try:
            return template.format(
                current_date=datetime.now().strftime("%Y-%m-%d-%H:%M:%S"),
                available_tools="\n".join(available_tools_str_list),
                user_request=user_request,
                sources_formatted=sources_formatted,
                deep_mode_instructions=deep_mode_instructions,
            )
        except KeyError as e:
            raise KeyError(f"Missing placeholder in system prompt template: {e}") from e

    @classmethod
    def get_last_resolved_prompt_path(cls) -> Optional[str]:
        return cls._last_resolved_prompt_path
