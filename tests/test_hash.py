"""Hash utilities tests."""

import pytest
from lit.core.hash import hash_object, hash_file
import tempfile
from pathlib import Path


def test_hash_object_empty():
    """Test hashing empty bytes."""
    result = hash_object(b'')
    assert len(result) == 40
    assert isinstance(result, str)


def test_hash_object_deterministic():
    """Test hash consistency for same input."""
    data = b'hello world'
    hash1 = hash_object(data)
    hash2 = hash_object(data)
    assert hash1 == hash2


def test_hash_object_different_data():
    """Test different data produces different hashes."""
    hash1 = hash_object(b'hello')
    hash2 = hash_object(b'world')
    assert hash1 != hash2


def test_hash_file():
    """Test hashing file contents."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('test content')
        temp_path = f.name
    
    try:
        result = hash_file(temp_path)
        assert len(result) == 40
        assert isinstance(result, str)
    finally:
        Path(temp_path).unlink()


def test_hash_file_deterministic():
    """Test file hash consistency."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('test content')
        temp_path = f.name
    
    try:
        hash1 = hash_file(temp_path)
        hash2 = hash_file(temp_path)
        assert hash1 == hash2
    finally:
        Path(temp_path).unlink()
