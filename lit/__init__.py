"""Lit - A Git-like version control system implemented in Python."""

__version__ = '0.1.0'
__author__ = 'Flambeau Iriho'
__email__ = 'irihoflambeau@gmail.com'

from lit.core.repository import Repository
from lit.core.objects import GitObject, Blob, Tree, Commit

__all__ = [
    'Repository',
    'GitObject',
    'Blob',
    'Tree',
    'Commit',
]
