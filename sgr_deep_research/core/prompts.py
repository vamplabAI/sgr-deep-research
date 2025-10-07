import os
from datetime import datetime
from functools import cache

from sgr_deep_research.core.models import SourceData
from sgr_deep_research.core.tools import BaseTool
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
        
        Returns static prompt without dynamic data (date, sources)
        to enable OpenAI prompt caching.
        
        Dynamically removes Confluence-related sections if Confluence is disabled.
        """
        template = cls._load_prompt_file(config.prompts.system_prompt_file)
        
        # Remove Confluence sections if disabled
        if config.confluence is None or not config.confluence.enabled:
            template = cls._remove_confluence_sections(template)
        
        return template
    
    @classmethod
    def _remove_confluence_sections(cls, prompt: str) -> str:
        """Remove Confluence-related sections from prompt when Confluence is disabled."""
        lines = prompt.split('\n')
        filtered_lines = []
        skip_until_next_section = False
        skip_context_section = False
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Skip CONTEXT section about Confluence
            if 'CONTEXT: You work for a company with internal Confluence' in line:
                skip_context_section = True
                i += 1
                continue
            
            # Stop skipping when we hit CORE PRINCIPLES
            if skip_context_section and 'CORE PRINCIPLES' in line:
                skip_context_section = False
                filtered_lines.append(line)
                i += 1
                continue
            
            if skip_context_section:
                i += 1
                continue
            
            # Check if this is a Confluence tool section (numbered items 3-5)
            if line.strip().startswith(('3. ConfluenceSearchTool', '4. ConfluenceSpaceSearchTool', '5. ConfluencePageTool')):
                skip_until_next_section = True
                i += 1
                continue
            
            # Check if we reached the next major section (AGENT CONTROL TOOLS)
            if skip_until_next_section and 'AGENT CONTROL TOOLS' in line:
                skip_until_next_section = False
                filtered_lines.append(line)
                i += 1
                continue
            
            # Skip lines that are part of Confluence tool descriptions
            if skip_until_next_section:
                i += 1
                continue
            
            # Remove Confluence-specific rules from "WHEN TO USE WHICH TOOL"
            if any(phrase in line for phrase in [
                'ConfluenceSearchTool', 
                'ConfluenceSpaceSearchTool',
                'Confluence FIRST',
                'internal/technical topics and people',
                'they might be an employee'
            ]):
                i += 1
                continue
            
            filtered_lines.append(line)
            i += 1
        
        # Renumber remaining tools in AGENT CONTROL TOOLS section
        result = '\n'.join(filtered_lines)
        
        # Fix tool numbering: 6-10 should become 3-7
        result = result.replace('6. ClarificationTool', '3. ClarificationTool')
        result = result.replace('7. GeneratePlanTool', '4. GeneratePlanTool')
        result = result.replace('8. AdaptPlanTool', '5. AdaptPlanTool')
        result = result.replace('9. CreateReportTool', '6. CreateReportTool')
        result = result.replace('10. AgentCompletionTool', '7. AgentCompletionTool')
        
        return result

    @classmethod
    def _get_current_date(cls) -> str:
        """Get current date in ISO format for user messages."""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    @classmethod
    def get_initial_user_request(cls, task: str) -> str:
        """Get formatted initial user request with current date.
        
        Date is included in user message to keep system prompt static for caching.
        """
        template = cls._load_prompt_file("initial_user_request.txt")
        return template.format(
            task=task,
            current_date=cls._get_current_date()
        )

    @classmethod
    def get_clarification_response(cls, clarifications: str) -> str:
        """Get formatted clarification response with current date.
        
        Date is included in user message to keep system prompt static for caching.
        """
        template = cls._load_prompt_file("clarification_response.txt")
        return template.format(
            clarifications=clarifications,
            current_date=cls._get_current_date()
        )
