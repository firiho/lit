"""Blob storage tests."""

import pytest
import tempfile
from pathlib import Path
from lit.core.objects import Blob


def test_blob_creation():
    """Test blob creation with data."""
    blob = Blob(b'hello world')
    assert blob.data == b'hello world'
    assert blob.type == 'blob'


def test_blob_serialize():
    """Test blob serialization."""
    blob = Blob(b'test data')
    serialized = blob.serialize()
    assert serialized == b'test data'


def test_blob_roundtrip():
    """Test blob serialize/deserialize cycle."""
    original_data = b'test content'
    blob1 = Blob(original_data)
    serialized = blob1.serialize()
    
    blob2 = Blob(b'')
    blob2.deserialize(serialized)
    assert blob2.data == original_data


def test_blob_hash():
    """Test blob hash computation."""
    blob = Blob(b'hello')
    hash_value = blob.compute_hash()
    assert len(hash_value) == 40
    assert isinstance(hash_value, str)


def test_blob_hash_deterministic():
    """Test blob hash determinism."""
    blob1 = Blob(b'same data')
    blob2 = Blob(b'same data')
    assert blob1.compute_hash() == blob2.compute_hash()


def test_blob_from_file():
    """Test blob creation from file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('file content')
        temp_path = f.name
    
    try:
        blob = Blob.from_file(temp_path)
        assert blob.data == b'file content'
    finally:
        Path(temp_path).unlink()
