"""Stash implementation for Lit VCS."""

import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

from lit.core.index import Index


@dataclass
class StashEntry:
    """
    Represents a single stash entry.
    
    Stores the index state, working tree changes, and metadata
    about when and where the stash was created.
    """
    message: str                    # User-provided or auto-generated message
    branch: str                     # Branch stash was created on
    commit: str                     # HEAD commit at time of stash
    timestamp: int                  # Unix timestamp
    index_tree: str                 # Tree hash of staged changes
    work_tree: str                  # Tree hash of working tree changes
    
    def __repr__(self) -> str:
        """String representation."""
        return f"StashEntry({self.message[:40]}...)"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StashEntry':
        """Create from dictionary."""
        return cls(**data)


class StashManager:
    """
    Manages the stash stack for a repository.
    
    The stash stores:
    - Working tree changes (modified tracked files)
    - Index changes (staged but not committed)
    
    Stashes are stored as a stack in .lit/stash.json
    """
    
    def __init__(self, repo):
        """
        Initialize stash manager.
        
        Args:
            repo: Repository instance
        """
        self.repo = repo
        self.stash_file = repo.lit_dir / 'stash.json'
    
    def _get_index(self) -> Index:
        """Load and return the current index."""
        index = Index()
        if self.repo.index_file.exists():
            index.read(str(self.repo.index_file))
        return index
    
    def _load_stashes(self) -> List[StashEntry]:
        """Load stash stack from disk."""
        if not self.stash_file.exists():
            return []
        
        try:
            data = json.loads(self.stash_file.read_text())
            return [StashEntry.from_dict(entry) for entry in data]
        except (json.JSONDecodeError, KeyError):
            return []
    
    def _save_stashes(self, stashes: List[StashEntry]) -> None:
        """Save stash stack to disk."""
        data = [entry.to_dict() for entry in stashes]
        self.stash_file.write_text(json.dumps(data, indent=2))
    
    def _build_tree_from_index(self) -> str:
        """
        Build a tree object from current index state.
        
        Returns:
            str: Tree hash
        """
        from lit.core.objects import Tree, Blob
        
        index = self._get_index()
        if not index.entries:
            return ""
        
        # Build tree structure from index entries
        root = {}
        
        for path, entry in index.entries.items():
            parts = path.split('/')
            current = root
            
            # Navigate/create directories
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Add file entry
            filename = parts[-1]
            current[filename] = (entry.sha1, entry.mode)
        
        return self._write_tree_recursive(root)
    
    def _write_tree_recursive(self, node: dict) -> str:
        """Recursively write tree objects."""
        from lit.core.objects import Tree
        
        tree = Tree()
        
        for name, value in sorted(node.items()):
            if isinstance(value, tuple):
                # It's a file (blob)
                sha1, mode = value
                # Normalize mode
                if mode & 0o111:  # Executable
                    mode_str = '100755'
                else:
                    mode_str = '100644'
                tree.add_entry(mode_str, 'blob', sha1, name)
            else:
                # It's a directory (subtree)
                subtree_hash = self._write_tree_recursive(value)
                tree.add_entry('040000', 'tree', subtree_hash, name)
        
        return self.repo.write_object(tree)
    
    def _build_tree_from_workdir(self) -> str:
        """
        Build a tree object from current working directory state.
        
        Only includes tracked files (files in index or last commit).
        
        Returns:
            str: Tree hash
        """
        from lit.core.objects import Tree, Blob
        
        index = self._get_index()
        
        # Get tracked files from index
        tracked_files = set(index.entries.keys())
        
        # Also include files from HEAD commit
        head = self.repo.refs.resolve_head()
        if head:
            commit = self.repo.read_object(head)
            if commit:
                tree_files = self._get_tree_files(commit.tree)
                tracked_files.update(tree_files.keys())
        
        # Build tree from working directory
        root = {}
        
        for path in tracked_files:
            full_path = self.repo.work_tree / path
            if not full_path.exists() or not full_path.is_file():
                continue
            
            # Create blob for file
            blob = Blob.from_file(str(full_path))
            sha1 = self.repo.write_object(blob)
            mode = full_path.stat().st_mode
            
            parts = path.split('/')
            current = root
            
            # Navigate/create directories
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Add file entry
            filename = parts[-1]
            current[filename] = (sha1, mode)
        
        if not root:
            return ""
        
        return self._write_tree_recursive(root)
    
    def _get_tree_files(self, tree_hash: str, prefix: str = "") -> Dict[str, str]:
        """
        Get all files from a tree recursively.
        
        Returns:
            Dict mapping path -> sha1
        """
        files = {}
        tree = self.repo.read_object(tree_hash)
        
        if not tree:
            return files
        
        for entry in tree.entries:
            path = f"{prefix}{entry.name}" if not prefix else f"{prefix}/{entry.name}"
            if entry.type == 'blob':
                files[path] = entry.hash
            elif entry.type == 'tree':
                files.update(self._get_tree_files(entry.hash, path))
        
        return files
    
    def save(self, message: Optional[str] = None, keep_index: bool = False) -> Optional[StashEntry]:
        """
        Save current changes to stash.
        
        Args:
            message: Optional stash message
            keep_index: If True, don't reset the index after stashing
            
        Returns:
            StashEntry if successful, None if nothing to stash
        """
        from lit.core.objects import Commit
        
        # Check if there are changes to stash
        index = self._get_index()
        head = self.repo.refs.resolve_head()
        
        if not head:
            return None
        
        # Get current branch
        head_content = (self.repo.lit_dir / 'HEAD').read_text().strip()
        if head_content.startswith('ref: refs/heads/'):
            branch = head_content[16:]
        else:
            branch = "(detached)"
        
        # Build trees for index and working directory
        index_tree = self._build_tree_from_index()
        work_tree = self._build_tree_from_workdir()
        
        # Check if there's anything to stash
        commit = self.repo.read_object(head)
        head_tree = commit.tree if commit else ""
        
        if index_tree == head_tree and work_tree == head_tree:
            return None  # Nothing to stash
        
        # Generate message
        if not message:
            message = f"WIP on {branch}: {head[:7]} {commit.message.split(chr(10))[0] if commit else ''}"
        
        # Create stash entry
        entry = StashEntry(
            message=message,
            branch=branch,
            commit=head,
            timestamp=int(time.time()),
            index_tree=index_tree,
            work_tree=work_tree
        )
        
        # Add to stash stack
        stashes = self._load_stashes()
        stashes.insert(0, entry)  # Push to top
        self._save_stashes(stashes)
        
        # Reset working directory and index to HEAD
        if not keep_index:
            self._reset_to_head()
        
        return entry
    
    def _reset_to_head(self) -> None:
        """Reset index and working directory to HEAD."""
        head = self.repo.refs.resolve_head()
        if not head:
            return
        
        commit = self.repo.read_object(head)
        if not commit:
            return
        
        # Clear index and rebuild from HEAD tree
        index = self._get_index()
        index.clear()
        
        # Restore files from tree
        tree_files = self._get_tree_files(commit.tree)
        
        for path, sha1 in tree_files.items():
            # Restore file content
            blob = self.repo.read_object(sha1)
            if blob:
                full_path = self.repo.work_tree / path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_bytes(blob.data)
                
                # Add to index
                stat = full_path.stat()
                index.add_entry(
                    path=path,
                    sha1=sha1,
                    mode=stat.st_mode,
                    size=stat.st_size,
                    mtime=int(stat.st_mtime),
                    ctime=int(stat.st_ctime)
                )
        
        # Write index
        index.write(str(self.repo.index_file))
    
    def list(self) -> List[StashEntry]:
        """
        List all stash entries.
        
        Returns:
            List of stash entries (most recent first)
        """
        return self._load_stashes()
    
    def apply(self, index: int = 0, pop: bool = False) -> Optional[StashEntry]:
        """
        Apply a stash entry to working directory.
        
        Args:
            index: Stash index (0 = most recent)
            pop: If True, remove the stash after applying
            
        Returns:
            Applied stash entry or None if index out of range
        """
        stashes = self._load_stashes()
        
        if index < 0 or index >= len(stashes):
            return None
        
        entry = stashes[index]
        
        # Restore working tree from stash
        if entry.work_tree:
            work_files = self._get_tree_files(entry.work_tree)
            
            for path, sha1 in work_files.items():
                blob = self.repo.read_object(sha1)
                if blob:
                    full_path = self.repo.work_tree / path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_bytes(blob.data)
        
        # Restore index from stash
        if entry.index_tree:
            index_obj = self._get_index()
            index_files = self._get_tree_files(entry.index_tree)
            
            for path, sha1 in index_files.items():
                full_path = self.repo.work_tree / path
                if full_path.exists():
                    stat = full_path.stat()
                    index_obj.add_entry(
                        path=path,
                        sha1=sha1,
                        mode=stat.st_mode,
                        size=stat.st_size,
                        mtime=int(stat.st_mtime),
                        ctime=int(stat.st_ctime)
                    )
            
            index_obj.write(str(self.repo.index_file))
        
        # Remove from stack if popping
        if pop:
            stashes.pop(index)
            self._save_stashes(stashes)
        
        return entry
    
    def pop(self, index: int = 0) -> Optional[StashEntry]:
        """
        Apply and remove a stash entry.
        
        Args:
            index: Stash index (0 = most recent)
            
        Returns:
            Popped stash entry or None if index out of range
        """
        return self.apply(index=index, pop=True)
    
    def drop(self, index: int = 0) -> Optional[StashEntry]:
        """
        Remove a stash entry without applying it.
        
        Args:
            index: Stash index (0 = most recent)
            
        Returns:
            Dropped stash entry or None if index out of range
        """
        stashes = self._load_stashes()
        
        if index < 0 or index >= len(stashes):
            return None
        
        entry = stashes.pop(index)
        self._save_stashes(stashes)
        
        return entry
    
    def clear(self) -> int:
        """
        Remove all stash entries.
        
        Returns:
            Number of entries cleared
        """
        stashes = self._load_stashes()
        count = len(stashes)
        
        if self.stash_file.exists():
            self.stash_file.unlink()
        
        return count
    
    def show(self, index: int = 0) -> Optional[Dict[str, Any]]:
        """
        Show details of a stash entry.
        
        Args:
            index: Stash index (0 = most recent)
            
        Returns:
            Dict with stash details or None if index out of range
        """
        stashes = self._load_stashes()
        
        if index < 0 or index >= len(stashes):
            return None
        
        entry = stashes[index]
        
        # Get files changed
        work_files = self._get_tree_files(entry.work_tree) if entry.work_tree else {}
        index_files = self._get_tree_files(entry.index_tree) if entry.index_tree else {}
        
        return {
            'entry': entry,
            'work_files': list(work_files.keys()),
            'index_files': list(index_files.keys())
        }
