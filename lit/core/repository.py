"""Repository management for Lit VCS."""

import os
import zlib
from pathlib import Path
from typing import Optional
from .objects import GitObject, Blob, Tree, Commit


class Repository:
    """
    Represents a Lit repository.
    
    A repository manages the .lit directory structure and provides
    methods for reading and writing Git objects.
    """
    
    def __init__(self, path: str = '.'):
        """
        Initialize repository.
        
        Args:
            path: Path to repository root (defaults to current directory)
        """
        self.work_tree = Path(path).resolve()
        self.lit_dir = self.work_tree / '.lit'
        self.objects_dir = self.lit_dir / 'objects'
        self.refs_dir = self.lit_dir / 'refs'
        self.heads_dir = self.refs_dir / 'heads'
        self.tags_dir = self.refs_dir / 'tags'
        self.remotes_dir = self.refs_dir / 'remotes'
        self.head_file = self.lit_dir / 'HEAD'
        self.index_file = self.lit_dir / 'index'
        self.config_file = self.lit_dir / 'config'
        
        # Initialize managers (lazy loading to avoid circular import)
        self._ref_manager = None
        self._diff_engine = None
        self._merge_engine = None
        self._remote_manager = None
    
    @property
    def refs(self):
        """Get RefManager instance."""
        if self._ref_manager is None:
            from .refs import RefManager
            self._ref_manager = RefManager(self)
        return self._ref_manager
    
    @property
    def diff(self):
        """Get DiffEngine instance."""
        if self._diff_engine is None:
            from .diff import DiffEngine
            self._diff_engine = DiffEngine(self)
        return self._diff_engine
    
    @property
    def merge(self):
        """Get MergeEngine instance."""
        if self._merge_engine is None:
            from .merge import MergeEngine
            self._merge_engine = MergeEngine(self)
        return self._merge_engine
    
    @property
    def remote(self):
        """Get RemoteManager instance."""
        if self._remote_manager is None:
            from .remote import RemoteManager
            self._remote_manager = RemoteManager(self)
        return self._remote_manager
    
    def init(self) -> 'Repository':
        """
        Initialize a new repository.
        
        Creates the .lit directory structure:
        .lit/
        ├── objects/       # Object database
        ├── refs/
        │   ├── heads/     # Branch references
        │   ├── tags/      # Tag references
        │   └── remotes/   # Remote references
        ├── HEAD           # Current branch/commit
        ├── index          # Staging area
        └── config         # Repository configuration
        
        Returns:
            Repository: self for method chaining
            
        Raises:
            Exception: If repository already exists
        """
        if self.lit_dir.exists():
            raise Exception(f"Repository already exists at {self.lit_dir}")
        
        # Create directory structure
        self.lit_dir.mkdir()
        self.objects_dir.mkdir()
        self.refs_dir.mkdir()
        self.heads_dir.mkdir()
        self.tags_dir.mkdir()
        self.remotes_dir.mkdir()
        
        # Initialize HEAD to point to main branch
        self.head_file.write_text('ref: refs/heads/main\n')
        
        # Initialize config
        config_content = '[core]\n\trepositoryformatversion = 0\n'
        self.config_file.write_text(config_content)
        
        return self
    
    @classmethod
    def find_repository(cls, path: str = '.') -> Optional['Repository']:
        """
        Find repository by searching up the directory tree.
        
        Searches from the given path upwards until it finds a .lit directory
        or reaches the filesystem root.
        
        Args:
            path: Starting path for search
            
        Returns:
            Repository if found, None otherwise
        """
        current = Path(path).resolve()
        
        while True:
            lit_dir = current / '.lit'
            if lit_dir.is_dir():
                return cls(str(current))
            
            # Reached filesystem root
            if current == current.parent:
                return None
            
            current = current.parent
    
    def object_path(self, hash: str) -> Path:
        """
        Get filesystem path for an object.
        
        Objects are stored in subdirectories named by the first 2 characters
        of the hash, with the remaining 38 characters as the filename.
        Example: ab/cdef0123456789... for hash abcdef0123456789...
        
        Args:
            hash: 40-character SHA-1 hash
            
        Returns:
            Path: Full path to object file
        """
        return self.objects_dir / hash[:2] / hash[2:]
    
    def write_object(self, obj: GitObject) -> str:
        """
        Write object to repository.
        
        Objects are stored compressed with zlib. The format is:
        <type> <size>\0<content>
        
        Args:
            obj: Git object to write
            
        Returns:
            str: SHA-1 hash of the object
        """
        hash = obj.hash
        path = self.object_path(hash)
        
        # Object already exists
        if path.exists():
            return hash
        
        # Prepare data with header
        data = obj.serialize()
        header = f"{obj.type} {len(data)}\0".encode()
        content = header + data
        
        # Compress and write
        compressed = zlib.compress(content)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(compressed)
        
        return hash
    
    def read_object(self, hash: str) -> GitObject:
        """
        Read object from repository.
        
        Args:
            hash: 40-character SHA-1 hash
            
        Returns:
            GitObject: Deserialized object (Blob, Tree, or Commit)
            
        Raises:
            Exception: If object not found or has invalid format
        """
        path = self.object_path(hash)
        
        if not path.exists():
            raise Exception(f"Object {hash} not found")
        
        # Read and decompress
        compressed = path.read_bytes()
        content = zlib.decompress(compressed)
        
        # Parse header: <type> <size>\0
        null_idx = content.index(b'\0')
        header = content[:null_idx].decode()
        data = content[null_idx + 1:]
        
        try:
            obj_type, size_str = header.split(' ', 1)
            size = int(size_str)
        except ValueError:
            raise Exception(f"Invalid object header: {header}")
        
        # Verify size
        if len(data) != size:
            raise Exception(f"Object size mismatch: expected {size}, got {len(data)}")
        
        # Create appropriate object type
        if obj_type == 'blob':
            obj = Blob()
        elif obj_type == 'tree':
            obj = Tree()
        elif obj_type == 'commit':
            obj = Commit()
        else:
            raise Exception(f"Unknown object type: {obj_type}")
        
        obj.deserialize(data)
        return obj
    
    def object_exists(self, hash: str) -> bool:
        """
        Check if object exists in repository.
        
        Args:
            hash: 40-character SHA-1 hash
            
        Returns:
            bool: True if object exists
        """
        return self.object_path(hash).exists()
    
    def __repr__(self) -> str:
        """String representation of repository."""
        return f"Repository(path={self.work_tree})"
