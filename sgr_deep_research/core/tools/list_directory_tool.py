from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import Field

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.tools.file_filters import (
    MAX_DIRECTORY_ITEMS,
    filter_paths,
)

if TYPE_CHECKING:
    from sgr_deep_research.core.models import ResearchContext

logger = logging.getLogger(__name__)


class ListDirectoryTool(BaseTool):
    """List files and directories in a given path.
    Use this tool to explore directory structure and discover available files.
    
    Usage:
        - Provide directory path to list contents
        - Returns files and subdirectories
        - Use to navigate and understand project structure
    """

    reasoning: str = Field(description="Why you need to list this directory and what you're looking for")
    directory_path: str = Field(description="Path to directory to list (absolute or relative)")
    recursive: bool = Field(default=False, description="List subdirectories recursively")

    async def __call__(self, context: ResearchContext) -> str:
        """List directory contents."""
        
        logger.info(f"📁 Listing directory: {self.directory_path}")
        
        try:
            dir_path = Path(self.directory_path)
            
            if not dir_path.exists():
                return f"Error: Directory not found: {self.directory_path}"
            
            if not dir_path.is_dir():
                return f"Error: Path is not a directory: {self.directory_path}"
            
            result = f"Directory: {self.directory_path}\n\n"
            
            if self.recursive:
                items = sorted(dir_path.rglob('*'))
                result += "Contents (recursive, filtered):\n"
            else:
                items = sorted(dir_path.iterdir())
                result += "Contents (filtered):\n"
            
            # Filter out ignored directories and files
            items = filter_paths(items)
            
            # Limit results
            if len(items) > MAX_DIRECTORY_ITEMS:
                result += f"Note: Showing first {MAX_DIRECTORY_ITEMS} of {len(items)} items\n\n"
                items = items[:MAX_DIRECTORY_ITEMS]
            
            dirs = []
            files = []
            
            for item in items:
                relative_path = item.relative_to(dir_path) if self.recursive else item.name
                if item.is_dir():
                    dirs.append(f"📁 {relative_path}/")
                else:
                    size = item.stat().st_size
                    files.append(f"📄 {relative_path} ({size} bytes)")
            
            if dirs:
                result += "\nDirectories:\n" + "\n".join(dirs) + "\n"
            if files:
                result += "\nFiles:\n" + "\n".join(files) + "\n"
            
            result += f"\nTotal: {len(dirs)} directories, {len(files)} files"
            
            logger.debug(f"Listed {len(items)} items in {self.directory_path}")
            return result
            
        except Exception as e:
            logger.error(f"Error listing directory {self.directory_path}: {e}")
            return f"Error listing directory: {str(e)}"

