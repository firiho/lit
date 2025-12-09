"""Backwards compatibility - merge module has moved to lit.operations.merge"""
from lit.operations.merge import MergeEngine, MergeResult, MergeConflict

__all__ = ['MergeEngine', 'MergeResult', 'MergeConflict']
