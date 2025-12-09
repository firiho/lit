"""Diff engine for comparing files and trees."""

from typing import List, Tuple, Optional
from difflib import unified_diff
from pathlib import Path


class DiffHunk:
    """Represents a single hunk (continuous block of changes) in a diff."""
    
    def __init__(self, old_start: int, old_count: int, new_start: int, new_count: int):
        self.old_start = old_start
        self.old_count = old_count
        self.new_start = new_start
        self.new_count = new_count
        self.lines = []
    
    def add_line(self, line: str):
        """Add a line to this hunk."""
        self.lines.append(line)
    
    def __str__(self):
        return f"@@ -{self.old_start},{self.old_count} +{self.new_start},{self.new_count} @@"


class FileDiff:
    """Represents the diff for a single file."""
    
    def __init__(self, path: str, old_content: Optional[bytes], new_content: Optional[bytes]):
        self.path = path
        self.old_content = old_content
        self.new_content = new_content
        self.is_new = old_content is None
        self.is_deleted = new_content is None
        self.is_modified = old_content is not None and new_content is not None
        self.hunks = []
    
    def compute_diff(self):
        """Compute diff hunks for this file."""
        if self.is_new:
            # New file - all lines are additions
            new_lines = self.new_content.decode('utf-8', errors='replace').splitlines(keepends=True)
            if new_lines:
                hunk = DiffHunk(0, 0, 1, len(new_lines))
                for line in new_lines:
                    hunk.add_line(f"+{line.rstrip()}")
                self.hunks.append(hunk)
        elif self.is_deleted:
            # Deleted file - all lines are deletions
            old_lines = self.old_content.decode('utf-8', errors='replace').splitlines(keepends=True)
            if old_lines:
                hunk = DiffHunk(1, len(old_lines), 0, 0)
                for line in old_lines:
                    hunk.add_line(f"-{line.rstrip()}")
                self.hunks.append(hunk)
        else:
            # Modified file - compute actual diff
            old_lines = self.old_content.decode('utf-8', errors='replace').splitlines(keepends=True)
            new_lines = self.new_content.decode('utf-8', errors='replace').splitlines(keepends=True)
            
            # Use unified_diff from difflib
            diff_lines = list(unified_diff(
                old_lines, new_lines,
                fromfile=f"a/{self.path}",
                tofile=f"b/{self.path}",
                lineterm=''
            ))
            
            if len(diff_lines) > 2:  # Skip if only headers
                self._parse_unified_diff(diff_lines[2:])  # Skip file headers
    
    def _parse_unified_diff(self, diff_lines: List[str]):
        """Parse unified diff output into hunks."""
        current_hunk = None
        
        for line in diff_lines:
            if line.startswith('@@'):
                # Parse hunk header
                # Format: @@ -old_start,old_count +new_start,new_count @@
                parts = line.split('@@')[1].strip().split()
                old_part = parts[0][1:]  # Remove '-'
                new_part = parts[1][1:]  # Remove '+'
                
                if ',' in old_part:
                    old_start, old_count = map(int, old_part.split(','))
                else:
                    old_start = int(old_part)
                    old_count = 1
                
                if ',' in new_part:
                    new_start, new_count = map(int, new_part.split(','))
                else:
                    new_start = int(new_part)
                    new_count = 1
                
                current_hunk = DiffHunk(old_start, old_count, new_start, new_count)
                self.hunks.append(current_hunk)
            elif current_hunk and (line.startswith('+') or line.startswith('-') or line.startswith(' ')):
                current_hunk.add_line(line.rstrip())


class DiffEngine:
    """
    Engine for computing diffs between files, trees, and commits.
    
    Supports:
    - Blob diffing (file content comparison)
    - Tree diffing (directory structure comparison)
    - Unified diff format output
    """
    
    def __init__(self, repo):
        """
        Initialize diff engine.
        
        Args:
            repo: Repository instance
        """
        self.repo = repo
    
    def diff_blobs(self, path: str, old_content: Optional[bytes], new_content: Optional[bytes]) -> FileDiff:
        """
        Compute diff between two blob contents.
        
        Args:
            path: File path
            old_content: Old file content (None for new files)
            new_content: New file content (None for deleted files)
        
        Returns:
            FileDiff object
        """
        file_diff = FileDiff(path, old_content, new_content)
        file_diff.compute_diff()
        return file_diff
    
    def diff_trees(self, old_tree_files: dict, new_tree_files: dict) -> List[FileDiff]:
        """
        Compute diff between two trees.
        
        Args:
            old_tree_files: Dict of {path: blob_hash} for old tree
            new_tree_files: Dict of {path: blob_hash} for new tree
        
        Returns:
            List of FileDiff objects
        """
        diffs = []
        
        # Find all unique paths
        all_paths = set(old_tree_files.keys()) | set(new_tree_files.keys())
        
        for path in sorted(all_paths):
            old_hash = old_tree_files.get(path)
            new_hash = new_tree_files.get(path)
            
            # Skip if unchanged
            if old_hash == new_hash:
                continue
            
            # Get blob contents
            old_content = None
            if old_hash:
                try:
                    old_blob = self.repo.read_object(old_hash)
                    old_content = old_blob.data
                except:
                    pass
            
            new_content = None
            if new_hash:
                try:
                    new_blob = self.repo.read_object(new_hash)
                    new_content = new_blob.data
                except:
                    pass
            
            # Compute diff
            diff = self.diff_blobs(path, old_content, new_content)
            diffs.append(diff)
        
        return diffs
    
    def diff_commits(self, old_commit_hash: Optional[str], new_commit_hash: str) -> List[FileDiff]:
        """
        Compute diff between two commits.
        
        Args:
            old_commit_hash: Old commit hash (None for initial commit)
            new_commit_hash: New commit hash
        
        Returns:
            List of FileDiff objects
        """
        from lit.core.objects import Commit, Tree
        
        # Get old tree
        old_tree_files = {}
        if old_commit_hash:
            old_commit = self.repo.read_object(old_commit_hash)
            if isinstance(old_commit, Commit):
                old_tree = self.repo.read_object(old_commit.tree)
                if isinstance(old_tree, Tree):
                    old_tree_files = self._get_tree_files(old_tree)
        
        # Get new tree
        new_commit = self.repo.read_object(new_commit_hash)
        if not isinstance(new_commit, Commit):
            return []
        
        new_tree = self.repo.read_object(new_commit.tree)
        if not isinstance(new_tree, Tree):
            return []
        
        new_tree_files = self._get_tree_files(new_tree)
        
        return self.diff_trees(old_tree_files, new_tree_files)
    
    def _get_tree_files(self, tree, prefix='') -> dict:
        """Recursively get all files from tree."""
        from lit.core.objects import Tree
        
        files = {}
        for entry in tree.entries:
            path = f"{prefix}{entry.name}" if prefix else entry.name
            
            if entry.type == 'blob':
                files[path] = entry.hash
            elif entry.type == 'tree':
                subtree = self.repo.read_object(entry.hash)
                if isinstance(subtree, Tree):
                    subfiles = self._get_tree_files(subtree, f"{path}/")
                    files.update(subfiles)
        
        return files
    
    def diff_working_to_index(self) -> List[FileDiff]:
        """
        Compute diff between working directory and index (staged changes).
        
        Returns:
            List of FileDiff objects
        """
        from lit.core.index import Index
        from lit.core.hash import hash_file
        
        # Get index
        index = Index()
        index_file = self.repo.index_file
        if index_file.exists():
            index.read(str(index_file))
        
        index_files = {entry.path: entry.sha1 for entry in index.entries.values()}
        
        # Get working directory files
        work_tree = self.repo.work_tree
        working_files = {}
        
        for path in work_tree.rglob('*'):
            if path.is_file():
                rel_path = path.relative_to(work_tree)
                
                if any(part.startswith('.') for part in rel_path.parts):
                    continue
                
                try:
                    working_files[str(rel_path)] = str(path)
                except:
                    pass
        
        # Compute diffs
        diffs = []
        all_paths = set(index_files.keys()) | set(working_files.keys())
        
        for path in sorted(all_paths):
            index_hash = index_files.get(path)
            working_path = working_files.get(path)
            
            # Quick hash comparison for files in index
            if index_hash and working_path:
                from lit.core.hash import hash_file
                try:
                    working_hash = hash_file(working_path)
                    if working_hash == index_hash:
                        # File unchanged, skip
                        continue
                except:
                    pass
            
            # Get content
            old_content = None
            if index_hash:
                try:
                    old_blob = self.repo.read_object(index_hash)
                    old_content = old_blob.data
                except:
                    pass
            
            new_content = None
            if working_path:
                try:
                    new_content = Path(working_path).read_bytes()
                except:
                    pass
            
            # Skip if unchanged (fallback check)
            if old_content == new_content:
                continue
            
            diff = self.diff_blobs(path, old_content, new_content)
            diffs.append(diff)
        
        return diffs
    
    def diff_index_to_head(self) -> List[FileDiff]:
        """
        Compute diff between index (staged) and HEAD.
        
        Returns:
            List of FileDiff objects
        """
        from lit.core.index import Index
        from lit.core.objects import Commit, Tree
        
        # Get HEAD tree
        head_files = {}
        refs_mgr = self.repo.refs
        head_commit_hash = refs_mgr.resolve_head()
        
        if head_commit_hash:
            head_commit = self.repo.read_object(head_commit_hash)
            if isinstance(head_commit, Commit):
                head_tree = self.repo.read_object(head_commit.tree)
                if isinstance(head_tree, Tree):
                    head_files = self._get_tree_files(head_tree)
        
        # Get index files
        index = Index()
        index_file = self.repo.index_file
        if index_file.exists():
            index.read(str(index_file))
        
        index_files = {entry.path: entry.sha1 for entry in index.entries.values()}
        
        return self.diff_trees(head_files, index_files)
    
    def format_diff(self, diffs: List[FileDiff], color: bool = True) -> str:
        """
        Format diffs as unified diff output.
        
        Args:
            diffs: List of FileDiff objects
            color: Whether to use color output
        
        Returns:
            Formatted diff string
        """
        from colorama import Fore, Style
        
        output = []
        
        for diff in diffs:
            # File header
            if diff.is_new:
                output.append(f"diff --lit a/{diff.path} b/{diff.path}")
                output.append("new file mode 100644")
                output.append(f"--- /dev/null")
                output.append(f"+++ b/{diff.path}")
            elif diff.is_deleted:
                output.append(f"diff --lit a/{diff.path} b/{diff.path}")
                output.append("deleted file mode 100644")
                output.append(f"--- a/{diff.path}")
                output.append(f"+++ /dev/null")
            else:
                output.append(f"diff --lit a/{diff.path} b/{diff.path}")
                output.append(f"--- a/{diff.path}")
                output.append(f"+++ b/{diff.path}")
            
            # Hunks
            for hunk in diff.hunks:
                if color:
                    output.append(f"{Fore.CYAN}{hunk}{Style.RESET_ALL}")
                else:
                    output.append(str(hunk))
                
                for line in hunk.lines:
                    if color:
                        if line.startswith('+'):
                            output.append(f"{Fore.GREEN}{line}{Style.RESET_ALL}")
                        elif line.startswith('-'):
                            output.append(f"{Fore.RED}{line}{Style.RESET_ALL}")
                        else:
                            output.append(line)
                    else:
                        output.append(line)
        
        return '\n'.join(output)
