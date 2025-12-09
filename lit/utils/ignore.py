"""Ignore pattern matching for .litignore files."""

import fnmatch
import re
from pathlib import Path
from typing import List, Optional, Set


class IgnorePattern:
    """Represents a single ignore pattern."""
    
    def __init__(self, pattern: str, negation: bool = False, directory_only: bool = False):
        """
        Initialize an ignore pattern.
        
        Args:
            pattern: The glob pattern to match
            negation: If True, this pattern negates (un-ignores) matching files
            directory_only: If True, only match directories
        """
        self.original = pattern
        self.pattern = pattern
        self.negation = negation
        self.directory_only = directory_only
        
        # Convert pattern to regex for more powerful matching
        self._regex = self._compile_pattern(pattern)
    
    def _compile_pattern(self, pattern: str) -> re.Pattern:
        """Convert a gitignore-style pattern to a regex."""
        # Handle ** (match any path segments)
        # Handle * (match anything except /)
        # Handle ? (match single character except /)
        
        regex_parts = []
        i = 0
        
        # Check if pattern is anchored (starts with /)
        anchored = pattern.startswith('/')
        if anchored:
            pattern = pattern[1:]
            regex_parts.append('^')
        
        while i < len(pattern):
            c = pattern[i]
            
            if c == '*':
                if i + 1 < len(pattern) and pattern[i + 1] == '*':
                    # ** matches any path
                    if i + 2 < len(pattern) and pattern[i + 2] == '/':
                        # **/ matches zero or more directories
                        regex_parts.append('(?:.*/)?')
                        i += 3
                    else:
                        # ** at end matches everything
                        regex_parts.append('.*')
                        i += 2
                else:
                    # * matches anything except /
                    regex_parts.append('[^/]*')
                    i += 1
            elif c == '?':
                # ? matches single character except /
                regex_parts.append('[^/]')
                i += 1
            elif c == '[':
                # Character class - find closing ]
                j = i + 1
                if j < len(pattern) and pattern[j] == '!':
                    j += 1
                if j < len(pattern) and pattern[j] == ']':
                    j += 1
                while j < len(pattern) and pattern[j] != ']':
                    j += 1
                if j < len(pattern):
                    # Valid character class
                    char_class = pattern[i:j+1]
                    # Convert ! to ^ for negation
                    if len(char_class) > 1 and char_class[1] == '!':
                        char_class = '[^' + char_class[2:]
                    regex_parts.append(char_class)
                    i = j + 1
                else:
                    # No closing ], treat [ as literal
                    regex_parts.append(re.escape(c))
                    i += 1
            elif c == '/':
                regex_parts.append('/')
                i += 1
            else:
                # Escape other special regex chars
                regex_parts.append(re.escape(c))
                i += 1
        
        # If not anchored and doesn't contain /, match anywhere in path
        if not anchored and '/' not in self.original.lstrip('/'):
            regex_str = '(?:^|/)' + ''.join(regex_parts) + '(?:/|$)'
        else:
            if not anchored:
                regex_str = '(?:^|/)' + ''.join(regex_parts)
            else:
                regex_str = ''.join(regex_parts)
            
            # Match to end or followed by /
            if not regex_str.endswith('.*'):
                regex_str += '(?:/.*)?$'
        
        return re.compile(regex_str)
    
    def matches(self, path: str, is_dir: bool = False) -> bool:
        """
        Check if a path matches this pattern.
        
        Args:
            path: The path to check (relative to repo root)
            is_dir: Whether the path is a directory
            
        Returns:
            True if the path matches this pattern
        """
        # Normalize path separators
        path = path.replace('\\', '/')
        if path.startswith('./'):
            path = path[2:]
        
        # For directory-only patterns (trailing /), we need to check
        # if the path IS the directory or is INSIDE the directory
        if self.directory_only:
            # Check if path matches exactly (for directories)
            if is_dir and self._regex.search(path):
                return True
            # Check if any parent directory matches
            parts = path.split('/')
            for i in range(len(parts)):
                parent = '/'.join(parts[:i+1])
                if self._regex.search(parent):
                    return True
            return False
        
        return bool(self._regex.search(path))


class IgnoreMatcher:
    """Matches paths against a set of ignore patterns."""
    
    def __init__(self):
        """Initialize empty matcher."""
        self.patterns: List[IgnorePattern] = []
        self._cache: dict = {}
    
    def add_pattern(self, pattern: str) -> None:
        """
        Add a pattern to the matcher.
        
        Args:
            pattern: A gitignore-style pattern
        """
        # Skip empty lines and comments
        pattern = pattern.strip()
        if not pattern or pattern.startswith('#'):
            return
        
        # Check for negation
        negation = False
        if pattern.startswith('!'):
            negation = True
            pattern = pattern[1:]
        
        # Check for directory-only (trailing /)
        directory_only = False
        if pattern.endswith('/'):
            directory_only = True
            pattern = pattern[:-1]
        
        self.patterns.append(IgnorePattern(pattern, negation, directory_only))
        self._cache.clear()
    
    def add_patterns(self, patterns: List[str]) -> None:
        """Add multiple patterns."""
        for pattern in patterns:
            self.add_pattern(pattern)
    
    def load_file(self, path: Path) -> bool:
        """
        Load patterns from an ignore file.
        
        Args:
            path: Path to the ignore file
            
        Returns:
            True if file was loaded successfully
        """
        if not path.exists():
            return False
        
        try:
            content = path.read_text()
            for line in content.splitlines():
                self.add_pattern(line)
            return True
        except Exception:
            return False
    
    def is_ignored(self, path: str, is_dir: bool = False) -> bool:
        """
        Check if a path should be ignored.
        
        The last matching pattern wins. Negation patterns can
        un-ignore previously ignored files.
        
        Args:
            path: The path to check (relative to repo root)
            is_dir: Whether the path is a directory
            
        Returns:
            True if the path should be ignored
        """
        # Check cache
        cache_key = (path, is_dir)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Normalize path
        path = path.replace('\\', '/')
        if path.startswith('./'):
            path = path[2:]
        
        # Check each pattern, last match wins
        ignored = False
        for pattern in self.patterns:
            if pattern.matches(path, is_dir):
                ignored = not pattern.negation
        
        self._cache[cache_key] = ignored
        return ignored
    
    def filter_paths(self, paths: List[str], is_dir_func=None) -> List[str]:
        """
        Filter a list of paths, removing ignored ones.
        
        Args:
            paths: List of paths to filter
            is_dir_func: Optional function to check if path is directory
            
        Returns:
            List of non-ignored paths
        """
        result = []
        for path in paths:
            is_dir = is_dir_func(path) if is_dir_func else False
            if not self.is_ignored(path, is_dir):
                result.append(path)
        return result


def get_ignore_matcher(repo_root: Path) -> IgnoreMatcher:
    """
    Create an IgnoreMatcher with default patterns for a repository.
    
    Loads patterns from:
    1. Built-in defaults (.lit directory)
    2. .litignore file in repo root
    
    Args:
        repo_root: Path to repository root
        
    Returns:
        Configured IgnoreMatcher instance
    """
    matcher = IgnoreMatcher()
    
    # Always ignore .lit directory
    matcher.add_pattern('.lit/')
    matcher.add_pattern('.lit')
    
    # Load .litignore if it exists
    litignore_path = repo_root / '.litignore'
    matcher.load_file(litignore_path)
    
    return matcher


# Common patterns for convenience
COMMON_IGNORE_PATTERNS = [
    # Python
    '__pycache__/',
    '*.py[cod]',
    '*$py.class',
    '.Python',
    'venv/',
    '.venv/',
    'env/',
    '.env',
    '*.egg-info/',
    'dist/',
    'build/',
    '.pytest_cache/',
    '.mypy_cache/',
    
    # Node.js
    'node_modules/',
    'npm-debug.log',
    
    # IDEs
    '.idea/',
    '.vscode/',
    '*.swp',
    '*.swo',
    '*~',
    
    # OS files
    '.DS_Store',
    'Thumbs.db',
    
    # Build outputs
    '*.o',
    '*.so',
    '*.dylib',
]
