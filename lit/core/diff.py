"""Backwards compatibility - diff module has moved to lit.operations.diff"""
from lit.operations.diff import DiffEngine, FileDiff, DiffHunk

__all__ = ['DiffEngine', 'FileDiff', 'DiffHunk']
