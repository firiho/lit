"""Hash utilities for Lit."""

import hashlib


def hash_object(data: bytes) -> str:
    """
    Compute SHA-1 hash of data.
    
    Args:
        data: Bytes to hash
        
    Returns:
        40-character hex string
    """
    return hashlib.sha1(data).hexdigest()


def hash_file(filepath: str) -> str:
    """
    Compute SHA-1 hash of file.
    
    Args:
        filepath: Path to file
        
    Returns:
        40-character hex string
    """
    with open(filepath, 'rb') as f:
        return hash_object(f.read())
