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


class ReadFileTool(BaseTool):
    """Read content from a file in the filesystem.
    Use this tool to examine file contents, understand code structure, or extract information.
    
    Usage:
        - Provide absolute or relative file paths
        - Optionally specify line range for large files
        - Use for reading source code, configs, documentation
    """

    reasoning: str = Field(description="Why you need to read this file and what you expect to find")
    file_path: str = Field(description="Path to the file to read (absolute or relative)")
    start_line: int | None = Field(default=None, description="Starting line number (1-based, optional)")
    end_line: int | None = Field(default=None, description="Ending line number (1-based, optional)")

    async def __call__(self, context: ResearchContext) -> str:
        """Read file content and return as string."""
        
        logger.info(f"📖 Reading file: {self.file_path}")
        
        try:
            file_path = Path(self.file_path)
            
            if not file_path.exists():
                return f"Error: File not found: {self.file_path}"
            
            if not file_path.is_file():
                return f"Error: Path is not a file: {self.file_path}"
            
            with open(file_path, 'r', encoding='utf-8') as f:
                if self.start_line is not None or self.end_line is not None:
                    lines = f.readlines()
                    start = (self.start_line - 1) if self.start_line else 0
                    end = self.end_line if self.end_line else len(lines)
                    content = ''.join(lines[start:end])
                else:
                    content = f.read()
            
            result = f"File: {self.file_path}\n"
            if self.start_line or self.end_line:
                result += f"Lines: {self.start_line or 1}-{self.end_line or 'end'}\n"
            result += f"\n{content}"
            
            logger.debug(f"Read {len(content)} characters from {self.file_path}")
            return result
            
        except UnicodeDecodeError:
            return f"Error: File is not a text file or has encoding issues: {self.file_path}"
        except Exception as e:
            logger.error(f"Error reading file {self.file_path}: {e}")
            return f"Error reading file: {str(e)}"

