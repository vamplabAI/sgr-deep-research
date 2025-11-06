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


class GetSystemPathsTool(BaseTool):
    """Get standard system paths and user directories.
    Use this tool to discover standard locations like home directory, documents, downloads, desktop, etc.
    
    Usage:
        - Find user's home directory
        - Discover standard folders (Documents, Downloads, Desktop)
        - Understand system structure before searching
    """

    reasoning: str = Field(description="Why you need to know system paths")

    async def __call__(self, context: ResearchContext) -> str:
        """Get system and user paths."""
        
        logger.info("🗺️ Getting system paths")
        
        try:
            result = "System Paths:\n\n"
            
            home = Path.home()
            result += f"Home Directory: {home}\n"
            result += f"  Exists: {home.exists()}\n\n"
            
            standard_dirs = {
                "Desktop": home / "Desktop",
                "Documents": home / "Documents",
                "Downloads": home / "Downloads",
                "Pictures": home / "Pictures",
                "Music": home / "Music",
                "Videos": home / "Videos",
            }
            
            result += "Standard User Directories:\n"
            for name, path in standard_dirs.items():
                exists = path.exists()
                result += f"  {name}: {path}\n"
                result += f"    Exists: {exists}\n"
                if exists:
                    try:
                        items = list(path.iterdir())
                        result += f"    Items: {len(items)}\n"
                    except PermissionError:
                        result += f"    Items: (permission denied)\n"
            
            result += f"\nCurrent Working Directory: {Path.cwd()}\n"
            
            result += f"\nEnvironment Variables:\n"
            if os.name == 'posix':
                result += f"  USER: {os.environ.get('USER', 'N/A')}\n"
                result += f"  HOME: {os.environ.get('HOME', 'N/A')}\n"
            elif os.name == 'nt':
                result += f"  USERNAME: {os.environ.get('USERNAME', 'N/A')}\n"
                result += f"  USERPROFILE: {os.environ.get('USERPROFILE', 'N/A')}\n"
            
            logger.debug(f"Home directory: {home}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting system paths: {e}")
            return f"Error getting system paths: {str(e)}"

