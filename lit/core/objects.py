"""Lit objects for Lit."""

from abc import ABC, abstractmethod
from typing import Optional
from .hash import hash_object


class LitObject(ABC):
    """Base class for all Lit objects."""
    
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
        
        Lit objects are hashed with a header containing the type and size.
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


class Blob(LitObject):
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


class TreeEntry:
    """
    Represents a single entry in a tree.
    
    Each entry contains:
    - mode: File permissions (e.g., '100644' for file, '040000' for directory)
    - type: Object type ('blob' or 'tree')
    - hash: SHA-1 hash of the object
    - name: Filename or directory name
    """
    
    def __init__(self, mode: str, obj_type: str, obj_hash: str, name: str):
        """
        Initialize tree entry.
        
        Args:
            mode: File mode (e.g., '100644', '100755', '040000')
            obj_type: Object type ('blob' or 'tree')
            obj_hash: SHA-1 hash of object
            name: Entry name
        """
        self.mode = mode
        self.type = obj_type
        self.hash = obj_hash
        self.name = name
    
    def __repr__(self) -> str:
        """String representation."""
        return f"TreeEntry({self.mode} {self.type} {self.hash[:7]} {self.name})"
    
    def __lt__(self, other: 'TreeEntry') -> bool:
        """Sort entries by name for consistent ordering."""
        return self.name < other.name


class Tree(LitObject):
    """
    Represents directory structure.
    
    A tree contains entries pointing to blobs (files) and other trees (subdirectories).
    """
    
    def __init__(self):
        """Initialize empty tree."""
        super().__init__()
        self.entries: list[TreeEntry] = []
    
    def add_entry(self, mode: str, obj_type: str, obj_hash: str, name: str) -> None:
        """
        Add entry to tree.
        
        Args:
            mode: File mode
            obj_type: Object type ('blob' or 'tree')
            obj_hash: Object hash
            name: Entry name
        """
        entry = TreeEntry(mode, obj_type, obj_hash, name)
        self.entries.append(entry)
        self.entries.sort()
        self._hash = None
    
    def serialize(self) -> bytes:
        """
        Serialize tree to Lit format.
        
        Format: <mode> <name>\0<20-byte hash>
        Each entry is: mode (as ASCII), space, name (as ASCII), null byte, hash (as binary)
        
        Returns:
            bytes: Serialized tree data
        """
        result = b''
        for entry in sorted(self.entries):
            mode_name = f"{entry.mode} {entry.name}".encode()
            hash_bytes = bytes.fromhex(entry.hash)
            result += mode_name + b'\0' + hash_bytes
        return result
    
    def deserialize(self, data: bytes) -> None:
        """
        Deserialize tree from Lit format.
        
        Args:
            data: Serialized tree data
        """
        self.entries = []
        pos = 0
        
        while pos < len(data):
            space_pos = data.index(b' ', pos)
            mode = data[pos:space_pos].decode()
            
            null_pos = data.index(b'\0', space_pos)
            name = data[space_pos + 1:null_pos].decode()
            
            hash_bytes = data[null_pos + 1:null_pos + 21]
            obj_hash = hash_bytes.hex()
            
            obj_type = 'tree' if mode == '040000' else 'blob'
            self.add_entry(mode, obj_type, obj_hash, name)
            
            pos = null_pos + 21
        
        self._hash = None
    
    @classmethod
    def from_directory(cls, repo, directory: str) -> 'Tree':
        """
        Build tree from directory contents.
        
        Args:
            repo: Repository instance
            directory: Path to directory
            
        Returns:
            Tree: New tree object
        """
        from pathlib import Path
        import stat
        
        tree = cls()
        dir_path = Path(directory)
        
        for item in sorted(dir_path.iterdir()):
            if item.name.startswith('.'):
                continue
            
            if item.is_file():
                blob = Blob.from_file(str(item))
                obj_hash = repo.write_object(blob)
                mode = '100755' if item.stat().st_mode & stat.S_IXUSR else '100644'
                tree.add_entry(mode, 'blob', obj_hash, item.name)
            
            elif item.is_dir():
                subtree = Tree.from_directory(repo, str(item))
                obj_hash = repo.write_object(subtree)
                tree.add_entry('040000', 'tree', obj_hash, item.name)
        
        return tree
    
    def __repr__(self) -> str:
        """String representation."""
        return f"Tree(entries={len(self.entries)})"


class Commit(LitObject):
    """
    Represents a commit with metadata.
    
    A commit captures:
    - Snapshot of project (tree hash)
    - Parent commit(s) for history
    - Author and committer info
    - Timestamp
    - Commit message
    """
    
    def __init__(self):
        """Initialize empty commit."""
        super().__init__()
        self.tree: str = ''
        self.parents: list[str] = []
        self.author: str = ''
        self.author_time: int = 0
        self.author_timezone: str = '+0000'
        self.committer: str = ''
        self.committer_time: int = 0
        self.committer_timezone: str = '+0000'
        self.message: str = ''
    
    def serialize(self) -> bytes:
        """
        Serialize commit to Lit format.
        
        Format:
        tree <tree-hash>
        parent <parent-hash>  (zero or more)
        author Name <email> <timestamp> <timezone>
        committer Name <email> <timestamp> <timezone>
        
        <commit message>
        
        Returns:
            bytes: Serialized commit data
        """
        lines = []
        
        lines.append(f'tree {self.tree}')
        
        for parent in self.parents:
            lines.append(f'parent {parent}')
        
        lines.append(f'author {self.author} {self.author_time} {self.author_timezone}')
        lines.append(f'committer {self.committer} {self.committer_time} {self.committer_timezone}')
        
        lines.append('')
        lines.append(self.message)
        
        return '\n'.join(lines).encode()
    
    def deserialize(self, data: bytes) -> None:
        """
        Deserialize commit from Lit format.
        
        Args:
            data: Serialized commit data
        """
        content = data.decode()
        lines = content.split('\n')
        
        message_start = 0
        for i, line in enumerate(lines):
            if not line:
                message_start = i + 1
                break
            
            if line.startswith('tree '):
                self.tree = line[5:]
            
            elif line.startswith('parent '):
                self.parents.append(line[7:])
            
            elif line.startswith('author '):
                parts = line[7:].rsplit(' ', 2)
                self.author = parts[0]
                self.author_time = int(parts[1])
                self.author_timezone = parts[2]
            
            elif line.startswith('committer '):
                parts = line[10:].rsplit(' ', 2)
                self.committer = parts[0]
                self.committer_time = int(parts[1])
                self.committer_timezone = parts[2]
        
        self.message = '\n'.join(lines[message_start:])
        self._hash = None
    
    @classmethod
    def create(
        cls,
        tree_hash: str,
        parent_hashes: list[str],
        author: str,
        committer: str,
        message: str,
        timestamp: Optional[int] = None,
        timezone: str = '+0000'
    ) -> 'Commit':
        """
        Create a new commit.
        
        Args:
            tree_hash: Hash of tree object
            parent_hashes: List of parent commit hashes
            author: Author name and email (e.g., "Name <email>")
            committer: Committer name and email
            message: Commit message
            timestamp: Unix timestamp (defaults to current time)
            timezone: Timezone offset (e.g., "+0000", "-0500")
            
        Returns:
            Commit: New commit object
        """
        import time
        
        commit = cls()
        commit.tree = tree_hash
        commit.parents = parent_hashes
        commit.author = author
        commit.committer = committer
        commit.message = message
        
        if timestamp is None:
            timestamp = int(time.time())
        
        commit.author_time = timestamp
        commit.committer_time = timestamp
        commit.author_timezone = timezone
        commit.committer_timezone = timezone
        
        return commit
    
    def __repr__(self) -> str:
        """String representation."""
        parent_info = f", parents={len(self.parents)}" if self.parents else ""
        msg_preview = self.message.split('\n')[0][:50]
        return f"Commit(hash={self.hash[:7]}{parent_info}, msg='{msg_preview}')"
