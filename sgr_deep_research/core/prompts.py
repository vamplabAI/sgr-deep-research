import os
from datetime import datetime
from functools import cache

from sgr_deep_research.core.tools import BaseTool
from sgr_deep_research.settings import PromptsConfig


class PromptLoader:
    @classmethod
    @cache
    def _load_prompt_file(cls, file_path: str) -> str:
        lib_file_path = os.path.join(os.path.dirname(__file__), "..", file_path)

        for file_path in [file_path, lib_file_path]:
            if os.path.exists(file_path):
                try:
                    with open(file_path, encoding="utf-8") as f:
                        return f.read().strip()
                except IOError as e:
                    raise IOError(f"Error reading prompt file {file_path}: {e}") from e

        raise FileNotFoundError(f"Prompt file not found: {file_path} or {lib_file_path}")

    @classmethod
    def get_system_prompt(cls, available_tools: list[BaseTool], prompts_config: PromptsConfig) -> str:
        template = cls._load_prompt_file(prompts_config.system_prompt_file)
        available_tools_str_list = [
            f"{i}. {tool.tool_name}: {tool.description}" for i, tool in enumerate(available_tools, start=1)
        ]
        try:
            return template.format(
                available_tools="\n".join(available_tools_str_list),
            )
        except KeyError as e:
            raise KeyError(f"Missing placeholder in system prompt template: {e}") from e

    @classmethod
    def get_initial_user_request(cls, task: str, prompts_config: PromptsConfig) -> str:
        template = cls._load_prompt_file(prompts_config.initial_user_request_file)
        return template.format(task=task, current_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    @classmethod
    def get_clarification_template(cls, clarifications: str, prompts_config: PromptsConfig) -> str:
        template = cls._load_prompt_file(prompts_config.clarification_response_file)
        return template.format(clarifications=clarifications, current_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
