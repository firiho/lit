"""Core functionality for Lit.

This module contains the core data structures:
- Git objects (Blob, Tree, Commit)
- Repository management
- Index/staging area
- Reference management
- Configuration management
- Hashing utilities

For operations like diff, merge, stash, see lit.operations
For remote operations, see lit.remote
For utilities like ignore, see lit.utils
"""

from lit.core.objects import GitObject, Blob, Tree, TreeEntry, Commit
from lit.core.repository import Repository
from lit.core.hash import hash_object, hash_file
from lit.core.index import Index, IndexEntry
from lit.core.refs import RefManager
from lit.core.config import Config, get_config

__all__ = [
    'GitObject',
    'Blob',
    'Tree',
    'TreeEntry',
    'Commit',
    'Repository',
    'Index',
    'IndexEntry',
    'RefManager',
    'Config',
    'get_config',
    'hash_object',
    'hash_file',
]
