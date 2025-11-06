from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import Field

from sgr_deep_research.core.base_tool import BaseTool
from sgr_deep_research.core.tools.file_filters import MAX_SEARCH_RESULTS

if TYPE_CHECKING:
    from sgr_deep_research.core.models import ResearchContext

logger = logging.getLogger(__name__)


class FindFilesFastTool(BaseTool):
    """Fast file search using native 'find' command (Unix/Mac only).
    Use this tool for efficient searching in large directories.
    Much faster than Python's recursive search for large file systems.
    
    Usage:
        - Search by name pattern (*.pdf, *.py)
        - Search by modification time (-mtime)
        - Search by size (-size)
        - Automatically excludes common ignore patterns
    """

    reasoning: str = Field(description="Why you need to search for these files")
    directory: str = Field(description="Directory to search in")
    name_pattern: str | None = Field(default=None, description="File name pattern (e.g., '*.pdf', '*.py')")
    modified_days: int | None = Field(default=None, description="Files modified within last N days")
    min_size: str | None = Field(default=None, description="Minimum size (e.g., '1M', '100k')")
    max_depth: int = Field(default=10, description="Maximum directory depth (default: 10)")

    async def __call__(self, context: ResearchContext) -> str:
        """Execute fast file search using native find command."""
        
        logger.info(f"🚀 Fast find in {self.directory}")
        
        try:
            search_path = Path(self.directory).expanduser()
            
            if not search_path.exists():
                return f"Error: Directory not found: {self.directory}"
            
            if not search_path.is_dir():
                return f"Error: Path is not a directory: {self.directory}"
            
            # Build find command
            cmd = ['find', str(search_path), '-maxdepth', str(self.max_depth), '-type', 'f']
            
            # Add name pattern
            if self.name_pattern:
                cmd.extend(['-name', self.name_pattern])
            
            # Add modification time
            if self.modified_days is not None:
                cmd.extend(['-mtime', f'-{self.modified_days}'])
            
            # Add size filter
            if self.min_size:
                cmd.extend(['-size', f'+{self.min_size}'])
            
            # Exclude common patterns
            exclude_patterns = [
                'node_modules', '__pycache__', '.git', '.venv', 'venv',
                '.cache', 'dist', 'build', '.idea', '.vscode'
            ]
            
            for pattern in exclude_patterns:
                cmd.extend(['-not', '-path', f'*/{pattern}/*'])
            
            # Execute find command with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
            except asyncio.TimeoutError:
                process.kill()
                return "Error: Search timed out after 30 seconds. Try searching in a more specific directory."
            
            if process.returncode != 0:
                stderr_text = stderr.decode('utf-8', errors='replace')
                return f"Error executing find command: {stderr_text}"
            
            # Parse results
            stdout_text = stdout.decode('utf-8', errors='replace')
            files = [line.strip() for line in stdout_text.split('\n') if line.strip()]
            
            # Limit results
            total_files = len(files)
            if total_files > MAX_SEARCH_RESULTS:
                files = files[:MAX_SEARCH_RESULTS]
            
            result = f"Fast Find Results:\n"
            result += f"Directory: {self.directory}\n"
            if self.name_pattern:
                result += f"Pattern: {self.name_pattern}\n"
            if self.modified_days:
                result += f"Modified within: {self.modified_days} days\n"
            if self.min_size:
                result += f"Min size: {self.min_size}\n"
            result += f"Max depth: {self.max_depth}\n"
            result += f"Excluded: {', '.join(exclude_patterns[:5])}...\n\n"
            
            if not files:
                result += "No files found matching the criteria."
                return result
            
            if total_files > MAX_SEARCH_RESULTS:
                result += f"Found {total_files} file(s), showing first {MAX_SEARCH_RESULTS}:\n\n"
            else:
                result += f"Found {len(files)} file(s):\n\n"
            
            for file_path in files:
                try:
                    path = Path(file_path)
                    size = path.stat().st_size
                    relative = path.relative_to(search_path) if path.is_relative_to(search_path) else path
                    result += f"📄 {relative} ({self._format_size(size)})\n"
                except Exception:
                    result += f"📄 {file_path}\n"
            
            logger.info(f"Found {total_files} files")
            return result
            
        except Exception as e:
            logger.error(f"Error in fast find: {e}")
            return f"Error: {str(e)}"
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

