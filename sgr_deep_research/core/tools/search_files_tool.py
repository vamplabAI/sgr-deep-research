from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import Field

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.tools.file_filters import (
    MAX_SEARCH_RESULTS,
    filter_paths,
)

if TYPE_CHECKING:
    from sgr_deep_research.core.models import ResearchContext

logger = logging.getLogger(__name__)


class SearchFilesTool(BaseTool):
    """Search for files by name pattern in the filesystem.
    Use this tool to find files matching specific patterns or names.
    
    Usage:
        - Provide search pattern (supports wildcards like *.py, config.*)
        - Specify directory to search in
        - Returns list of matching file paths
    """

    reasoning: str = Field(description="Why you need to search for these files and what you'll do with them")
    pattern: str = Field(description="File name pattern to search for (e.g., '*.py', 'config.*', 'test_*')")
    directory: str = Field(default=".", description="Directory to search in (default: current directory)")
    recursive: bool = Field(default=True, description="Search in subdirectories recursively")

    async def __call__(self, context: ResearchContext) -> str:
        """Search for files matching pattern."""
        
        logger.info(f"🔍 Searching files: pattern='{self.pattern}' in {self.directory}")
        
        try:
            search_path = Path(self.directory)
            
            if not search_path.exists():
                return f"Error: Directory not found: {self.directory}"
            
            if not search_path.is_dir():
                return f"Error: Path is not a directory: {self.directory}"
            
            if self.recursive:
                matches = list(search_path.rglob(self.pattern))
            else:
                matches = list(search_path.glob(self.pattern))
            
            matches = [m for m in matches if m.is_file()]
            
            # Filter out ignored files
            matches = filter_paths(matches)
            matches.sort()
            
            # Limit results
            total_matches = len(matches)
            if total_matches > MAX_SEARCH_RESULTS:
                matches = matches[:MAX_SEARCH_RESULTS]
            
            result = f"Search pattern: {self.pattern}\n"
            result += f"Directory: {self.directory}\n"
            result += f"Recursive: {self.recursive}\n"
            result += f"Filtered: Yes (excluding caches, venv, etc.)\n\n"
            
            if not matches:
                result += "No files found matching the pattern."
                return result
            
            if total_matches > MAX_SEARCH_RESULTS:
                result += f"Found {total_matches} file(s), showing first {MAX_SEARCH_RESULTS}:\n\n"
            else:
                result += f"Found {len(matches)} file(s):\n\n"
            
            for match in matches:
                relative_path = match.relative_to(search_path)
                size = match.stat().st_size
                result += f"📄 {relative_path} ({size} bytes)\n"
            
            logger.debug(f"Found {len(matches)} files matching '{self.pattern}'")
            return result
            
        except Exception as e:
            logger.error(f"Error searching files with pattern '{self.pattern}': {e}")
            return f"Error searching files: {str(e)}"

