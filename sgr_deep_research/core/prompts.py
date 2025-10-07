import os
from datetime import datetime
from functools import cache

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
    @cache
    def get_system_prompt(cls) -> str:
        """Get static system prompt for caching optimization.

        Returns static prompt without dynamic data (date, sources) to
        enable OpenAI prompt caching.
        """
        template = cls._load_prompt_file(config.prompts.system_prompt_file)
        return template

    @classmethod
    def _get_current_date(cls) -> str:
        """Get current date in ISO format for user messages."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def get_initial_user_request(cls, task: str) -> str:
        """Get formatted initial user request with current date.

        Date is included in user message to keep system prompt static
        for caching.
        """
        template = cls._load_prompt_file("initial_user_request.txt")
        return template.format(task=task, current_date=cls._get_current_date())

    @classmethod
    def get_clarification_response(cls, clarifications: str) -> str:
        """Get formatted clarification response with current date.

        Date is included in user message to keep system prompt static
        for caching.
        """
        template = cls._load_prompt_file("clarification_response.txt")
        return template.format(clarifications=clarifications, current_date=cls._get_current_date())
