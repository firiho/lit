"""Operations module for high-level Git operations.

This module contains the business logic for Git operations like:
- Diff computation
- Merge algorithms
- Stash management
- Checkout logic
- Status computation
"""

from lit.operations.diff import DiffEngine, FileDiff, DiffHunk
from lit.operations.merge import MergeEngine, MergeResult, MergeConflict
from lit.operations.stash import StashManager, StashEntry

__all__ = [
    'DiffEngine', 'FileDiff', 'DiffHunk',
    'MergeEngine', 'MergeResult', 'MergeConflict',
    'StashManager', 'StashEntry',
]
