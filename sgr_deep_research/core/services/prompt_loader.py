from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sgr_deep_research.core.agent_definition import PromptsConfig
    from sgr_deep_research.core.tools import BaseTool


class PromptLoader:
    @classmethod
    def get_system_prompt(cls, available_tools: list["BaseTool"], prompts_config: "PromptsConfig") -> str:
        template = prompts_config.system_prompt
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
    def get_initial_user_request(cls, task: str, prompts_config: "PromptsConfig") -> str:
        template = prompts_config.initial_user_request
        return template.format(task=task, current_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    @classmethod
    def get_clarification_template(cls, clarifications: str, prompts_config: "PromptsConfig") -> str:
        template = prompts_config.clarification_response
        return template.format(clarifications=clarifications, current_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
