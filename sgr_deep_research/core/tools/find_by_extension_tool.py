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


class FindByExtensionTool(BaseTool):
    """Find files by file extension in the filesystem.
    Use this tool to locate all files with specific extensions.
    
    Usage:
        - Find all Python files (.py)
        - Find all configuration files (.yaml, .json, .toml)
        - Find all documentation files (.md, .txt)
        - Support multiple extensions at once
    """

    reasoning: str = Field(description="Why you need to find files by extension and what you'll do with them")
    directory: str = Field(default=".", description="Directory to search in")
    extensions: list[str] = Field(description="List of file extensions to search for (e.g., ['py', 'js', 'ts'])")
    recursive: bool = Field(default=True, description="Search in subdirectories recursively")
    group_by_extension: bool = Field(default=False, description="Group results by file extension")

    async def __call__(self, context: ResearchContext) -> str:
        """Find files by extension."""
        
        logger.info(f"🔍 Finding files with extensions {self.extensions} in {self.directory}")
        
        try:
            search_path = Path(self.directory)
            
            if not search_path.exists():
                return f"Error: Directory not found: {self.directory}"
            
            if not search_path.is_dir():
                return f"Error: Path is not a directory: {self.directory}"
            
            normalized_extensions = [ext.lower().lstrip('.') for ext in self.extensions]
            
            if self.recursive:
                all_files = []
                try:
                    for item in search_path.rglob('*'):
                        if len(all_files) > 10000:  # Safety limit
                            logger.warning(f"Reached safety limit of 10000 files during search")
                            break
                        all_files.append(item)
                except PermissionError as e:
                    logger.warning(f"Permission denied accessing some directories: {e}")
            else:
                try:
                    all_files = list(search_path.glob('*'))
                except PermissionError as e:
                    return f"Error: Permission denied: {e}"
            
            matching_files = []
            for file_path in all_files:
                try:
                    if file_path.is_file():
                        file_ext = file_path.suffix.lower().lstrip('.')
                        if file_ext in normalized_extensions:
                            matching_files.append(file_path)
                except (PermissionError, OSError):
                    continue
            
            # Filter out ignored files
            matching_files = filter_paths(matching_files)
            matching_files.sort()
            
            # Limit results
            total_matches = len(matching_files)
            if total_matches > MAX_SEARCH_RESULTS:
                matching_files = matching_files[:MAX_SEARCH_RESULTS]
            
            result = f"Search directory: {self.directory}\n"
            result += f"Extensions: {', '.join(self.extensions)}\n"
            result += f"Recursive: {self.recursive}\n"
            result += f"Filtered: Yes (excluding caches, venv, etc.)\n\n"
            
            if not matching_files:
                result += "No files found with specified extensions."
                return result
            
            if total_matches > MAX_SEARCH_RESULTS:
                result += f"Found {total_matches} file(s), showing first {MAX_SEARCH_RESULTS}:\n\n"
            else:
                result += f"Found {len(matching_files)} file(s):\n\n"
            
            if self.group_by_extension:
                grouped = {}
                for file_path in matching_files:
                    ext = file_path.suffix.lower().lstrip('.')
                    if ext not in grouped:
                        grouped[ext] = []
                    grouped[ext].append(file_path)
                
                for ext in sorted(grouped.keys()):
                    result += f"\n.{ext} files ({len(grouped[ext])}):\n"
                    for file_path in grouped[ext]:
                        relative_path = file_path.relative_to(search_path)
                        size = file_path.stat().st_size
                        result += f"  📄 {relative_path} ({size} bytes)\n"
            else:
                for file_path in matching_files:
                    relative_path = file_path.relative_to(search_path)
                    size = file_path.stat().st_size
                    result += f"📄 {relative_path} ({size} bytes)\n"
            
            logger.debug(f"Found {len(matching_files)} files with extensions {self.extensions}")
            return result
            
        except Exception as e:
            logger.error(f"Error finding files by extension: {e}")
            return f"Error finding files by extension: {str(e)}"

