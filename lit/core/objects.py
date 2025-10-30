"""Git objects for Lit."""

from abc import ABC, abstractmethod
from typing import Optional
from .hash import hash_object


class GitObject(ABC):
    """Base class for all Git objects."""
    
    def __init__(self):
        self._hash: Optional[str] = None
    
    @abstractmethod
    def serialize(self) -> bytes:
        """
        Serialize object to bytes.
        
        Returns:
            bytes: Serialized object data
        """
        pass
    
    @abstractmethod
    def deserialize(self, data: bytes) -> None:
        """
        Deserialize object from bytes.
        
        Args:
            data: Serialized object data
        """
        pass
    
    @property
    def type(self) -> str:
        """
        Return object type name.
        
        Returns:
            str: Object type (blob, tree, commit)
        """
        return self.__class__.__name__.lower()
    
    def compute_hash(self) -> str:
        """
        Compute and cache object hash.
        
        Git objects are hashed with a header containing the type and size.
        Format: <type> <size>\0<content>
        
        Returns:
            str: 40-character SHA-1 hash
        """
        if self._hash is None:
            data = self.serialize()
            header = f"{self.type} {len(data)}\0".encode()
            self._hash = hash_object(header + data)
        return self._hash
    
    @property
    def hash(self) -> str:
        """
        Get object hash.
        
        Returns:
            str: 40-character SHA-1 hash
        """
        return self.compute_hash()


class Blob(GitObject):
    """
    Represents file content.
    
    A blob stores the raw content of a file without any metadata
    like filename or permissions.
    """
    
    def __init__(self, data: Optional[bytes] = None):
        """
        Initialize a blob.
        
        Args:
            data: File content as bytes
        """
        super().__init__()
        self.data = data or b''
    
    def serialize(self) -> bytes:
        """
        Serialize blob to bytes.
        
        Returns:
            bytes: Raw file content
        """
        return self.data
    
    def deserialize(self, data: bytes) -> None:
        """
        Deserialize blob from bytes.
        
        Args:
            data: Raw file content
        """
        self.data = data
    
    @classmethod
    def from_file(cls, filepath: str) -> 'Blob':
        """
        Create blob from file.
        
        Args:
            filepath: Path to file
            
        Returns:
            Blob: New blob containing file content
        """
        with open(filepath, 'rb') as f:
            return cls(f.read())
    
    def __repr__(self) -> str:
        """String representation of blob."""
        size = len(self.data)
        return f"Blob(hash={self.hash[:7]}, size={size})"


class Tree(GitObject):
    """Represents directory structure."""
    
    def serialize(self) -> bytes:
        """Serialize tree to bytes."""
        # Placeholder - will be implemented later
        return b''
    
    def deserialize(self, data: bytes) -> None:
        """Deserialize tree from bytes."""
        # Placeholder - will be implemented later
        pass


class Commit(GitObject):
    """Represents a commit."""
    
    def serialize(self) -> bytes:
        """Serialize commit to bytes."""
        # Placeholder - will be implemented later
        return b''
    
    def deserialize(self, data: bytes) -> None:
        """Deserialize commit from bytes."""
        # Placeholder - will be implemented later
        pass
