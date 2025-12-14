"""Index (staging area) implementation."""

import struct
import hashlib
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass


@dataclass
class IndexEntry:
    """
    Represents a single entry in the index.
    
    Stores metadata about a staged file including timestamps,
    permissions, and the hash of its content.
    """
    ctime: int          # Creation time (seconds)
    ctime_ns: int       # Creation time (nanoseconds)
    mtime: int          # Modification time (seconds)
    mtime_ns: int       # Modification time (nanoseconds)
    dev: int            # Device ID
    ino: int            # Inode number
    mode: int           # File mode/permissions
    uid: int            # User ID
    gid: int            # Group ID
    size: int           # File size
    sha1: str           # SHA-1 hash of content
    flags: int          # Flags (includes name length)
    path: str           # File path
    
    def __repr__(self) -> str:
        """String representation."""
        return f"IndexEntry({self.mode:o} {self.sha1[:7]} {self.path})"


class Index:
    """
    Lit index (staging area) implementation.
    
    The index stores a list of files to be included in the next commit.
    Each entry contains file metadata and a hash of the file content.
    """
    
    def __init__(self):
        """Initialize empty index."""
        self.entries: Dict[str, IndexEntry] = {}
        self.version: int = 2
    
    def add_entry(
        self,
        path: str,
        sha1: str,
        mode: int,
        size: int,
        mtime: int = 0,
        mtime_ns: int = 0,
        ctime: int = 0,
        ctime_ns: int = 0,
        dev: int = 0,
        ino: int = 0,
        uid: int = 0,
        gid: int = 0
    ) -> None:
        """
        Add or update entry in index.
        
        Args:
            path: File path relative to repository root
            sha1: SHA-1 hash of file content
            mode: File mode/permissions
            size: File size in bytes
            mtime: Modification time (seconds)
            mtime_ns: Modification time (nanoseconds)
            ctime: Creation time (seconds)
            ctime_ns: Creation time (nanoseconds)
            dev: Device ID
            ino: Inode number
            uid: User ID
            gid: Group ID
        """
        flags = len(path.encode()) & 0xFFF
        
        entry = IndexEntry(
            ctime=ctime,
            ctime_ns=ctime_ns,
            mtime=mtime,
            mtime_ns=mtime_ns,
            dev=dev,
            ino=ino,
            mode=mode,
            uid=uid,
            gid=gid,
            size=size,
            sha1=sha1,
            flags=flags,
            path=path
        )
        
        self.entries[path] = entry
    
    def add_file(self, repo, filepath: str) -> str:
        """
        Stage a file for commit.
        
        Args:
            repo: Repository instance
            filepath: Path to file (absolute or relative)
            
        Returns:
            str: SHA-1 hash of staged content
        """
        from .objects import Blob
        import os
        
        file_path = Path(filepath)
        
        if not file_path.is_absolute():
            file_path = repo.work_tree / file_path
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        if not file_path.is_file():
            raise ValueError(f"Not a file: {filepath}")
        
        blob = Blob.from_file(str(file_path))
        sha1 = repo.write_object(blob)
        
        stat = file_path.stat()
        rel_path = str(file_path.relative_to(repo.work_tree))
        
        self.add_entry(
            path=rel_path,
            sha1=sha1,
            mode=stat.st_mode,
            size=stat.st_size,
            mtime=int(stat.st_mtime),
            mtime_ns=int((stat.st_mtime % 1) * 1e9),
            ctime=int(stat.st_ctime),
            ctime_ns=int((stat.st_ctime % 1) * 1e9),
            dev=stat.st_dev,
            ino=stat.st_ino,
            uid=stat.st_uid,
            gid=stat.st_gid
        )
        
        # Auto-persist to disk (like lit add)
        if hasattr(repo, 'index_file'):
            self.write(str(repo.index_file))
        
        return sha1
    
    def remove_entry(self, path: str, repo=None) -> None:
        """
        Remove entry from index.
        
        Args:
            path: Path to remove
            repo: Optional repository instance for auto-persistence
        """
        if path in self.entries:
            del self.entries[path]
            
            # Auto-persist to disk (like lit rm)
            if repo and hasattr(repo, 'index_file'):
                self.write(str(repo.index_file))
    
    def get_entry(self, path: str) -> Optional[IndexEntry]:
        """Get entry by path."""
        return self.entries.get(path)
    
    def clear(self) -> None:
        """Clear all entries from index."""
        self.entries.clear()
    
    def write(self, index_path: str) -> None:
        """
        Write index to disk in Lit binary format.
        
        Format:
        - Header: 'DIRC' + version (4 bytes) + entry count (4 bytes)
        - Entries: sorted by path, each with metadata + path
        - Checksum: SHA-1 of entire index
        
        Args:
            index_path: Path to index file
        """
        content = bytearray()
        
        # Header: signature, version, entry count
        content.extend(b'DIRC')
        content.extend(struct.pack('>I', self.version))
        content.extend(struct.pack('>I', len(self.entries)))
        
        # Entries (sorted by path)
        for path in sorted(self.entries.keys()):
            entry = self.entries[path]
            
            # Entry data (62 bytes fixed + variable path)
            entry_data = struct.pack(
                '>IIIIIIIIII20sH',
                entry.ctime,
                entry.ctime_ns,
                entry.mtime,
                entry.mtime_ns,
                entry.dev,
                entry.ino,
                entry.mode,
                entry.uid,
                entry.gid,
                entry.size,
                bytes.fromhex(entry.sha1),
                entry.flags
            )
            
            content.extend(entry_data)
            content.extend(entry.path.encode())
            content.extend(b'\x00')  # Null terminator
            
            # Padding to 8-byte alignment
            entry_len = len(entry_data) + len(entry.path.encode()) + 1
            padlen = (8 - (entry_len % 8)) % 8
            content.extend(b'\x00' * padlen)
        
        # Checksum
        checksum = hashlib.sha1(content).digest()
        content.extend(checksum)
        
        # Write to file
        Path(index_path).write_bytes(content)
    
    def read(self, index_path: str) -> None:
        """
        Read index from disk.
        
        Args:
            index_path: Path to index file
        """
        if not Path(index_path).exists():
            self.entries.clear()
            return
        
        data = Path(index_path).read_bytes()
        
        # Verify checksum
        content = data[:-20]
        checksum = data[-20:]
        expected = hashlib.sha1(content).digest()
        
        if checksum != expected:
            raise ValueError("Index checksum mismatch")
        
        # Parse header
        signature = data[0:4]
        if signature != b'DIRC':
            raise ValueError(f"Invalid index signature: {signature}")
        
        self.version = struct.unpack('>I', data[4:8])[0]
        entry_count = struct.unpack('>I', data[8:12])[0]
        
        # Parse entries
        self.entries.clear()
        offset = 12
        
        for _ in range(entry_count):
            # Fixed-size entry data (62 bytes)
            entry_data = struct.unpack('>IIIIIIIIII20sH', data[offset:offset+62])
            offset += 62
            
            # Variable-length path
            path_end = data.index(b'\x00', offset)
            path = data[offset:path_end].decode()
            offset = path_end + 1
            
            # Calculate padding to 8-byte alignment
            entry_len = 62 + len(path.encode()) + 1
            padlen = (8 - (entry_len % 8)) % 8
            offset += padlen
            
            # Create entry
            entry = IndexEntry(
                ctime=entry_data[0],
                ctime_ns=entry_data[1],
                mtime=entry_data[2],
                mtime_ns=entry_data[3],
                dev=entry_data[4],
                ino=entry_data[5],
                mode=entry_data[6],
                uid=entry_data[7],
                gid=entry_data[8],
                size=entry_data[9],
                sha1=entry_data[10].hex(),
                flags=entry_data[11],
                path=path
            )
            
            self.entries[path] = entry
    
    def __len__(self) -> int:
        """Number of entries in index."""
        return len(self.entries)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"Index(entries={len(self.entries)})"
