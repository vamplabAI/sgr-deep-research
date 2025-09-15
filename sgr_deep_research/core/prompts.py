import os
from functools import cache

from sgr_deep_research.core.models import SourceData
from sgr_deep_research.settings import get_config

config = get_config()


class PromptLoader:
    @classmethod
    @cache
    def _load_prompt_file(cls, filename: str) -> str:
        user_file_path = os.path.join(config.prompts.prompts_dir, filename)
        lib_file_path = os.path.join(os.path.dirname(__file__), "..", config.prompts.prompts_dir, filename)

        for file_path in [user_file_path, lib_file_path]:
            if os.path.exists(file_path):
                try:
                    with open(file_path, encoding="utf-8") as f:
                        return f.read().strip()
                except IOError as e:
                    raise IOError(f"Error reading prompt file {file_path}: {e}") from e

        raise FileNotFoundError(f"Prompt file not found: {user_file_path} or {lib_file_path}")

    @classmethod
    def get_tool_function_prompt(cls) -> str:
        return cls._load_prompt_file(config.prompts.tool_function_prompt_file)

    @classmethod
    def get_system_prompt(cls, user_request: str, sources: list[SourceData], deep_level: int = 0) -> str:
        sources_formatted = "\n".join([str(source) for source in sources])
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
                user_request=user_request, 
                sources_formatted=sources_formatted,
                deep_mode_instructions=deep_mode_instructions
            )
        except KeyError as e:
            raise KeyError(f"Missing placeholder in system prompt template: {e}") from e
