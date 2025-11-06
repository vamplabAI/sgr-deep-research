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


class FindBySizeTool(BaseTool):
    """Find files by size criteria in the filesystem.
    Use this tool to locate files based on their size (larger than, smaller than, or exact size).
    
    Usage:
        - Specify size in bytes, KB, MB, or GB
        - Find files larger or smaller than specified size
        - Useful for finding large files, empty files, or files of specific size
    """

    reasoning: str = Field(description="Why you need to find files by size and what you'll do with them")
    directory: str = Field(default=".", description="Directory to search in")
    min_size_bytes: int | None = Field(default=None, description="Minimum file size in bytes")
    max_size_bytes: int | None = Field(default=None, description="Maximum file size in bytes")
    recursive: bool = Field(default=True, description="Search in subdirectories recursively")

    async def __call__(self, context: ResearchContext) -> str:
        """Find files by size criteria."""
        
        logger.info(f"🔍 Finding files by size in {self.directory}")
        
        try:
            search_path = Path(self.directory)
            
            if not search_path.exists():
                return f"Error: Directory not found: {self.directory}"
            
            if not search_path.is_dir():
                return f"Error: Path is not a directory: {self.directory}"
            
            if self.recursive:
                files = []
                try:
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
                    size = file_path.stat().st_size
                except (PermissionError, OSError):
                    continue
                
                if self.min_size_bytes is not None and size < self.min_size_bytes:
                    continue
                if self.max_size_bytes is not None and size > self.max_size_bytes:
                    continue
                
                matching_files.append((file_path, size))
            
            matching_files.sort(key=lambda x: x[1], reverse=True)
            
            # Limit results
            total_matches = len(matching_files)
            if total_matches > MAX_SEARCH_RESULTS:
                matching_files = matching_files[:MAX_SEARCH_RESULTS]
            
            result = f"Search directory: {self.directory}\n"
            result += f"Recursive: {self.recursive}\n"
            result += f"Filtered: Yes (excluding caches, venv, etc.)\n"
            if self.min_size_bytes is not None:
                result += f"Minimum size: {self._format_size(self.min_size_bytes)}\n"
            if self.max_size_bytes is not None:
                result += f"Maximum size: {self._format_size(self.max_size_bytes)}\n"
            result += "\n"
            
            if not matching_files:
                result += "No files found matching the size criteria."
                return result
            
            if total_matches > MAX_SEARCH_RESULTS:
                result += f"Found {total_matches} file(s), showing first {MAX_SEARCH_RESULTS}:\n\n"
            else:
                result += f"Found {len(matching_files)} file(s):\n\n"
            
            for file_path, size in matching_files:
                relative_path = file_path.relative_to(search_path)
                result += f"📄 {relative_path} - {self._format_size(size)}\n"
            
            logger.debug(f"Found {len(matching_files)} files matching size criteria")
            return result
            
        except Exception as e:
            logger.error(f"Error finding files by size: {e}")
            return f"Error finding files by size: {str(e)}"
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"

