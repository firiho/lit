"""Utilities module for common helper functions.

This module contains:
- Filesystem utilities
- Path manipulation
- Ignore file handling (.litignore)
- Compression utilities
"""

from lit.utils.ignore import IgnoreMatcher, IgnorePattern

__all__ = [
    'IgnoreMatcher', 'IgnorePattern',
]
