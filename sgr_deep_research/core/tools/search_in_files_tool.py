from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import Field

from sgr_deep_research.core.base_tool import BaseTool

if TYPE_CHECKING:
    from sgr_deep_research.core.models import ResearchContext

logger = logging.getLogger(__name__)


class SearchInFilesTool(BaseTool):
    """Search for text content within files (like grep).
    Use this tool to find specific text, code patterns, or keywords across files.
    
    Usage:
        - Provide search text or regex pattern
        - Specify directory and file patterns to search in
        - Returns matching lines with file paths and line numbers
    """

    reasoning: str = Field(description="Why you need to search for this text and what you expect to find")
    search_text: str = Field(description="Text or regex pattern to search for")
    directory: str = Field(default=".", description="Directory to search in")
    file_pattern: str = Field(default="*", description="File pattern to search in (e.g., '*.py', '*.js')")
    case_sensitive: bool = Field(default=True, description="Case sensitive search")
    regex: bool = Field(default=False, description="Treat search_text as regex pattern")
    max_results: int = Field(default=50, description="Maximum number of results to return")

    async def __call__(self, context: ResearchContext) -> str:
        """Search for text in files."""
        
        logger.info(f"🔍 Searching in files: '{self.search_text}' in {self.directory}")
        
        try:
            search_path = Path(self.directory)
            
            if not search_path.exists():
                return f"Error: Directory not found: {self.directory}"
            
            if not search_path.is_dir():
                return f"Error: Path is not a directory: {self.directory}"
            
            files = list(search_path.rglob(self.file_pattern))
            files = [f for f in files if f.is_file()]
            
            flags = 0 if self.case_sensitive else re.IGNORECASE
            if self.regex:
                try:
                    pattern = re.compile(self.search_text, flags)
                except re.error as e:
                    return f"Error: Invalid regex pattern: {e}"
            else:
                pattern = re.compile(re.escape(self.search_text), flags)
            
            results = []
            total_matches = 0
            
            for file_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            if pattern.search(line):
                                if len(results) < self.max_results:
                                    relative_path = file_path.relative_to(search_path)
                                    results.append({
                                        'file': str(relative_path),
                                        'line': line_num,
                                        'content': line.rstrip()
                                    })
                                total_matches += 1
                except (UnicodeDecodeError, PermissionError):
                    continue
            
            result = f"Search text: {self.search_text}\n"
            result += f"Directory: {self.directory}\n"
            result += f"File pattern: {self.file_pattern}\n"
            result += f"Case sensitive: {self.case_sensitive}\n"
            result += f"Regex: {self.regex}\n\n"
            
            if not results:
                result += "No matches found."
                return result
            
            result += f"Found {total_matches} match(es)"
            if total_matches > self.max_results:
                result += f" (showing first {self.max_results})"
            result += ":\n\n"
            
            for match in results:
                result += f"{match['file']}:{match['line']}: {match['content']}\n"
            
            logger.debug(f"Found {total_matches} matches for '{self.search_text}'")
            return result
            
        except Exception as e:
            logger.error(f"Error searching in files: {e}")
            return f"Error searching in files: {str(e)}"

