from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import Field

from sgr_deep_research.core.base_tool import BaseTool

if TYPE_CHECKING:
    from sgr_deep_research.core.models import ResearchContext

logger = logging.getLogger(__name__)


class GetCurrentDirectoryTool(BaseTool):
    """Get current working directory and basic information about it.
    Use this tool to understand where the agent is currently located in the filesystem.
    
    Usage:
        - Find out current working directory
        - Get absolute path of current location
        - Understand the context before searching files
    """

    reasoning: str = Field(description="Why you need to know current directory")

    async def __call__(self, context: ResearchContext) -> str:
        """Get current working directory information."""
        
        logger.info("📍 Getting current directory")
        
        try:
            cwd = Path.cwd()
            abs_path = cwd.absolute()
            
            result = f"Current Working Directory:\n"
            result += f"Path: {abs_path}\n"
            result += f"Directory name: {cwd.name}\n\n"
            
            parent = cwd.parent
            result += f"Parent directory: {parent}\n\n"
            
            try:
                items = list(cwd.iterdir())
                dirs = [item.name for item in items if item.is_dir()]
                files = [item.name for item in items if item.is_file()]
                
                result += f"Contents summary:\n"
                result += f"  Directories: {len(dirs)}\n"
                result += f"  Files: {len(files)}\n"
                
                if dirs:
                    result += f"\nFirst few directories: {', '.join(dirs[:5])}"
                    if len(dirs) > 5:
                        result += f" ... and {len(dirs) - 5} more"
                
            except PermissionError:
                result += "Cannot list directory contents (permission denied)\n"
            
            logger.debug(f"Current directory: {abs_path}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting current directory: {e}")
            return f"Error getting current directory: {str(e)}"

