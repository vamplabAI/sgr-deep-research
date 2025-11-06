from __future__ import annotations

import logging
from datetime import datetime
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


class FindByDateTool(BaseTool):
    """Find files by modification date in the filesystem.
    Use this tool to locate files modified within a specific time range.
    
    Usage:
        - Find recently modified files
        - Find old files that haven't been touched
        - Search by modification date range
    """

    reasoning: str = Field(description="Why you need to find files by date and what you'll do with them")
    directory: str = Field(default=".", description="Directory to search in")
    days_ago: int | None = Field(default=None, description="Find files modified within last N days")
    older_than_days: int | None = Field(default=None, description="Find files older than N days")
    recursive: bool = Field(default=True, description="Search in subdirectories recursively")

    async def __call__(self, context: ResearchContext) -> str:
        """Find files by modification date."""
        
        logger.info(f"🔍 Finding files by date in {self.directory}")
        
        try:
            search_path = Path(self.directory)
            
            if not search_path.exists():
                return f"Error: Directory not found: {self.directory}"
            
            if not search_path.is_dir():
                return f"Error: Path is not a directory: {self.directory}"
            
            now = datetime.now()
            
            if self.recursive:
                files = []
                try:
                    # Limit recursion to avoid hanging on large directories
                    for item in search_path.rglob('*'):
                        if len(files) > 10000:  # Safety limit
                            logger.warning(f"Reached safety limit of 10000 files during search")
                            break
                        files.append(item)
                except PermissionError as e:
                    logger.warning(f"Permission denied accessing some directories: {e}")
            else:
                try:
                    files = list(search_path.glob('*'))
                except PermissionError as e:
                    return f"Error: Permission denied: {e}"
            
            files = [f for f in files if f.is_file()]
            
            # Filter out ignored files
            files = filter_paths(files)
            
            matching_files = []
            for file_path in files:
                try:
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    days_diff = (now - mtime).days
                    
                    if self.days_ago is not None and days_diff > self.days_ago:
                        continue
                    if self.older_than_days is not None and days_diff < self.older_than_days:
                        continue
                    
                    matching_files.append((file_path, mtime))
                except (PermissionError, OSError) as e:
                    # Skip files we can't access
                    logger.debug(f"Skipping file due to error: {file_path} - {e}")
                    continue
            
            matching_files.sort(key=lambda x: x[1], reverse=True)
            
            # Limit results
            total_matches = len(matching_files)
            if total_matches > MAX_SEARCH_RESULTS:
                matching_files = matching_files[:MAX_SEARCH_RESULTS]
            
            result = f"Search directory: {self.directory}\n"
            result += f"Recursive: {self.recursive}\n"
            result += f"Filtered: Yes (excluding caches, venv, etc.)\n"
            if self.days_ago is not None:
                result += f"Modified within last: {self.days_ago} days\n"
            if self.older_than_days is not None:
                result += f"Older than: {self.older_than_days} days\n"
            result += "\n"
            
            if not matching_files:
                result += "No files found matching the date criteria."
                return result
            
            if total_matches > MAX_SEARCH_RESULTS:
                result += f"Found {total_matches} file(s), showing first {MAX_SEARCH_RESULTS}:\n\n"
            else:
                result += f"Found {len(matching_files)} file(s):\n\n"
            
            for file_path, mtime in matching_files:
                relative_path = file_path.relative_to(search_path)
                result += f"📄 {relative_path} - modified {mtime.strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            logger.debug(f"Found {len(matching_files)} files matching date criteria")
            return result
            
        except Exception as e:
            logger.error(f"Error finding files by date: {e}")
            return f"Error finding files by date: {str(e)}"

