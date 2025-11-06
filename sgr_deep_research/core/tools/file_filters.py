"""File and directory filters for file system tools."""

from pathlib import Path

# Directories to ignore during file search
IGNORED_DIRECTORIES = {
    # Python
    '__pycache__',
    '.pytest_cache',
    '.mypy_cache',
    '.ruff_cache',
    'venv',
    '.venv',
    'env',
    '.env',
    'virtualenv',
    '.tox',
    'eggs',
    '.eggs',
    '*.egg-info',
    'dist',
    'build',
    '.pyenv',
    
    # Node.js
    'node_modules',
    '.npm',
    '.yarn',
    
    # Version control
    '.git',
    '.svn',
    '.hg',
    '.bzr',
    
    # IDEs
    '.vscode',
    '.idea',
    '.vs',
    '.eclipse',
    
    # OS
    '.DS_Store',
    'Thumbs.db',
    
    # Caches
    '.cache',
    'cache',
    '.temp',
    'temp',
    'tmp',
    
    # Build artifacts
    'target',
    'out',
    'bin',
    'obj',
}

# File patterns to ignore
IGNORED_FILE_PATTERNS = {
    '*.pyc',
    '*.pyo',
    '*.pyd',
    '*.so',
    '*.dll',
    '*.dylib',
    '*.class',
    '*.o',
    '*.obj',
    '.DS_Store',
    'Thumbs.db',
    '*.log',
    '*.swp',
    '*.swo',
    '*~',
}

# Maximum items to return from directory listing
MAX_DIRECTORY_ITEMS = 100

# Maximum files to return from search
MAX_SEARCH_RESULTS = 50

# Maximum depth for recursive search (to prevent hanging on large directories)
MAX_RECURSION_DEPTH = 5

# Timeout for file operations in seconds
FILE_OPERATION_TIMEOUT = 30


def should_ignore_directory(path: Path) -> bool:
    """Check if directory should be ignored."""
    name = path.name
    
    # Check exact matches
    if name in IGNORED_DIRECTORIES:
        return True
    
    # Check if it's a hidden directory (starts with .)
    if name.startswith('.') and name not in {'.', '..'}:
        return True
    
    return False


def should_ignore_file(path: Path) -> bool:
    """Check if file should be ignored."""
    name = path.name
    
    # Check exact matches
    if name in IGNORED_FILE_PATTERNS:
        return True
    
    # Check patterns
    for pattern in IGNORED_FILE_PATTERNS:
        if pattern.startswith('*'):
            suffix = pattern[1:]
            if name.endswith(suffix):
                return True
    
    return False


def filter_paths(paths: list[Path], include_hidden: bool = False) -> list[Path]:
    """Filter paths to exclude ignored directories and files."""
    filtered = []
    
    for path in paths:
        # Check if any parent directory should be ignored
        should_skip = False
        for parent in path.parents:
            if should_ignore_directory(parent):
                should_skip = True
                break
        
        if should_skip:
            continue
        
        # Check if the path itself should be ignored
        if path.is_dir():
            if should_ignore_directory(path):
                continue
        elif path.is_file():
            if should_ignore_file(path):
                continue
        
        filtered.append(path)
    
    return filtered

