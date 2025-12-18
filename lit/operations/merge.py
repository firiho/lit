"""Merge operations for Lit VCS."""

from pathlib import Path
from typing import Optional, List, Set, Tuple, Dict
from dataclasses import dataclass


@dataclass
class MergeConflict:
    """Represents a merge conflict in a file."""
    path: str
    base_content: Optional[bytes]
    ours_content: Optional[bytes]
    theirs_content: Optional[bytes]
    
    def __repr__(self) -> str:
        """String representation."""
        return f"MergeConflict({self.path})"


@dataclass
class MergeResult:
    """Result of a merge operation."""
    success: bool
    conflicts: List[MergeConflict]
    merged_tree_hash: Optional[str] = None
    is_fast_forward: bool = False
    message: str = ""
    
    def __repr__(self) -> str:
        """String representation."""
        if self.success:
            if self.is_fast_forward:
                return f"MergeResult(fast-forward, conflicts=0)"
            return f"MergeResult(success, conflicts={len(self.conflicts)})"
        return f"MergeResult(failed, conflicts={len(self.conflicts)})"


class MergeEngine:
    """
    Handles merge operations for Lit VCS.
    
    Supports:
    - Fast-forward merges
    - Three-way merges
    - Merge base finding (common ancestor)
    - Conflict detection
    - OT-inspired auto-merge (optional)
    """
    
    def __init__(self, repo):
        """
        Initialize merge engine.
        
        Args:
            repo: Repository instance
        """
        self.repo = repo
        self._auto_resolve = False  # OT auto-merge flag
        self._auto_resolve = False  # OT auto-merge flag
    
    @property
    def auto_resolve(self) -> bool:
        """Whether OT auto-merge is enabled."""
        return self._auto_resolve
    
    @auto_resolve.setter
    def auto_resolve(self, value: bool):
        """Enable or disable OT auto-merge."""
        self._auto_resolve = value
    
    def find_merge_base(self, commit1_hash: str, commit2_hash: str) -> Optional[str]:
        """
        Find the common ancestor (merge base) of two commits.
        
        Uses a breadth-first search to find the first common ancestor
        in the commit history graph.
        
        Args:
            commit1_hash: First commit hash
            commit2_hash: Second commit hash
            
        Returns:
            Hash of merge base commit, or None if no common ancestor
        """
        from lit.core.objects import Commit
        
        # Handle same commit
        if commit1_hash == commit2_hash:
            return commit1_hash
        
        # Build ancestor sets for both commits
        ancestors1 = self._get_ancestors(commit1_hash)
        ancestors2 = self._get_ancestors(commit2_hash)
        
        # Find common ancestors
        common_ancestors = ancestors1 & ancestors2
        
        if not common_ancestors:
            return None
        
        # Find the best common ancestor (closest to both commits)
        # This is the one that has the shortest distance sum to both commits
        best_ancestor = None
        min_distance = float('inf')
        
        for ancestor in common_ancestors:
            dist1 = self._distance_to_commit(commit1_hash, ancestor)
            dist2 = self._distance_to_commit(commit2_hash, ancestor)
            total_dist = dist1 + dist2
            
            if total_dist < min_distance:
                min_distance = total_dist
                best_ancestor = ancestor
        
        return best_ancestor
    
    def _get_ancestors(self, commit_hash: str) -> Set[str]:
        """
        Get all ancestors of a commit.
        
        Args:
            commit_hash: Starting commit hash
            
        Returns:
            Set of ancestor commit hashes (including the commit itself)
        """
        from lit.core.objects import Commit
        
        ancestors = set()
        to_visit = [commit_hash]
        visited = set()
        
        while to_visit:
            current = to_visit.pop(0)
            
            if current in visited:
                continue
            
            visited.add(current)
            ancestors.add(current)
            
            try:
                commit = self.repo.read_object(current)
                if isinstance(commit, Commit):
                    for parent in commit.parents:
                        if parent not in visited:
                            to_visit.append(parent)
            except:
                pass
        
        return ancestors
    
    def _distance_to_commit(self, start_hash: str, target_hash: str) -> int:
        """
        Calculate distance (number of commits) from start to target.
        
        Args:
            start_hash: Starting commit hash
            target_hash: Target commit hash
            
        Returns:
            Number of commits in path, or infinity if no path exists
        """
        from lit.core.objects import Commit
        
        if start_hash == target_hash:
            return 0
        
        to_visit = [(start_hash, 0)]
        visited = set()
        
        while to_visit:
            current, distance = to_visit.pop(0)
            
            if current == target_hash:
                return distance
            
            if current in visited:
                continue
            
            visited.add(current)
            
            try:
                commit = self.repo.read_object(current)
                if isinstance(commit, Commit):
                    for parent in commit.parents:
                        if parent not in visited:
                            to_visit.append((parent, distance + 1))
            except:
                pass
        
        return float('inf')
    
    def can_fast_forward(self, current_hash: str, target_hash: str) -> bool:
        """
        Check if we can fast-forward from current to target.
        
        A fast-forward is possible when target is a direct descendant
        of current (i.e., current is an ancestor of target).
        
        Args:
            current_hash: Current commit hash
            target_hash: Target commit hash
            
        Returns:
            True if fast-forward is possible
        """
        # Get all ancestors of target
        target_ancestors = self._get_ancestors(target_hash)
        
        # Current must be in target's ancestors for fast-forward
        return current_hash in target_ancestors
    
    def fast_forward(self, target_hash: str) -> MergeResult:
        """
        Perform a fast-forward merge to target commit.
        
        Args:
            target_hash: Target commit hash
            
        Returns:
            MergeResult indicating success
        """
        from lit.core.objects import Commit
        
        # Update HEAD to point to target
        current_branch = self.repo.refs.get_current_branch()
        
        if current_branch:
            # Update branch reference
            self.repo.refs.write_ref(f"refs/heads/{current_branch}", target_hash)
        else:
            # Detached HEAD - just update HEAD
            self.repo.head_file.write_text(target_hash + "\n")
        
        # Update working tree to match target commit
        commit = self.repo.read_object(target_hash)
        if isinstance(commit, Commit):
            self.repo.remote._checkout_commit(self.repo, commit)
        
        return MergeResult(
            success=True,
            conflicts=[],
            merged_tree_hash=None,
            is_fast_forward=True,
            message=f"Fast-forward to {target_hash[:7]}"
        )
    
    def three_way_merge(
        self,
        base_hash: str,
        ours_hash: str,
        theirs_hash: str,
        auto_strategy: Optional[str] = None,
        theirs_branch: Optional[str] = None
    ) -> MergeResult:
        """
        Perform a three-way merge.
        
        Merges changes from 'theirs' into 'ours' based on common ancestor 'base'.
        
        Args:
            base_hash: Common ancestor commit hash
            ours_hash: Our current commit hash
            theirs_hash: Their commit hash to merge in
            auto_strategy: Strategy for auto-resolving conflicts
            theirs_branch: Name of the branch being merged in (for messages)
            
        Returns:
            MergeResult with success status and any conflicts
        """
        from lit.core.objects import Commit, Tree
        
        # Get trees for all three commits
        base_commit = self.repo.read_object(base_hash)
        ours_commit = self.repo.read_object(ours_hash)
        theirs_commit = self.repo.read_object(theirs_hash)
        
        if not all(isinstance(c, Commit) for c in [base_commit, ours_commit, theirs_commit]):
            return MergeResult(
                success=False,
                conflicts=[],
                message="Invalid commit objects"
            )
        
        base_tree = self.repo.read_object(base_commit.tree)
        ours_tree = self.repo.read_object(ours_commit.tree)
        theirs_tree = self.repo.read_object(theirs_commit.tree)
        
        if not all(isinstance(t, Tree) for t in [base_tree, ours_tree, theirs_tree]):
            return MergeResult(
                success=False,
                conflicts=[],
                message="Invalid tree objects"
            )
        
        # Get file dictionaries from trees
        base_files = self._get_tree_files(base_tree)
        ours_files = self._get_tree_files(ours_tree)
        theirs_files = self._get_tree_files(theirs_tree)
        
        # For 'recent' strategy, we need to know which commit is more recent
        ours_is_recent = True  # Default: ours is more recent (we're merging theirs into ours)
        if auto_strategy == 'recent':
            # Compare commit timestamps if available
            try:
                ours_time = ours_commit.committer_time if hasattr(ours_commit, 'committer_time') else 0
                theirs_time = theirs_commit.committer_time if hasattr(theirs_commit, 'committer_time') else 0
                ours_is_recent = ours_time >= theirs_time
            except:
                pass  # Default to ours if we can't determine
        
        # Perform three-way merge
        merged_files, conflicts = self._merge_files(
            base_files, ours_files, theirs_files, 
            auto_strategy=auto_strategy,
            ours_is_recent=ours_is_recent,
            theirs_branch=theirs_branch
        )
        
        if conflicts:
            return MergeResult(
                success=False,
                conflicts=conflicts,
                message=f"Merge conflicts in {len(conflicts)} file(s)"
            )
        
        # Create merged tree
        merged_tree = Tree()
        for path, file_hash in merged_files.items():
            merged_tree.add_entry('100644', 'blob', file_hash, path)
        
        merged_tree_hash = self.repo.write_object(merged_tree)
        
        return MergeResult(
            success=True,
            conflicts=[],
            merged_tree_hash=merged_tree_hash,
            is_fast_forward=False,
            message=f"Merged {theirs_hash[:7]} into {ours_hash[:7]}"
        )
    
    def _get_tree_files(self, tree) -> Dict[str, str]:
        """
        Get all files in a tree as a flat dictionary.
        
        Args:
            tree: Tree object
            
        Returns:
            Dict mapping file paths to blob hashes
        """
        from lit.core.objects import Tree
        
        files = {}
        
        for entry in tree.entries:
            if entry.type == 'blob':
                files[entry.name] = entry.hash
            elif entry.type == 'tree':
                # Recursively get files from subtree
                subtree = self.repo.read_object(entry.hash)
                if isinstance(subtree, Tree):
                    subfiles = self._get_tree_files(subtree)
                    for path, file_hash in subfiles.items():
                        files[f"{entry.name}/{path}"] = file_hash
        
        return files
    
    def _merge_files(
        self,
        base_files: Dict[str, str],
        ours_files: Dict[str, str],
        theirs_files: Dict[str, str],
        auto_strategy: Optional[str] = None,
        ours_is_recent: bool = True,
        theirs_branch: Optional[str] = None
    ) -> Tuple[Dict[str, str], List[MergeConflict]]:
        """
        Merge file dictionaries using three-way merge logic.
        
        Args:
            base_files: Files in base (common ancestor)
            ours_files: Files in our branch
            theirs_files: Files in their branch
            auto_strategy: Strategy for auto-resolving conflicts
            ours_is_recent: Whether ours is the more recent commit
            theirs_branch: Name of the branch being merged in (for messages)
            
        Returns:
            Tuple of (merged_files, conflicts)
        """
        merged_files = {}
        conflicts = []
        
        # Get all file paths across all three versions
        all_paths = set(base_files.keys()) | set(ours_files.keys()) | set(theirs_files.keys())
        
        for path in sorted(all_paths):
            base_hash = base_files.get(path)
            ours_hash = ours_files.get(path)
            theirs_hash = theirs_files.get(path)
            
            # Case 1: File unchanged in both branches (or same change)
            if ours_hash == theirs_hash:
                if ours_hash:
                    merged_files[path] = ours_hash
                # If both deleted, don't include in merged
                continue
            
            # Case 2: File only changed in our branch
            if base_hash == theirs_hash and ours_hash != base_hash:
                if ours_hash:
                    merged_files[path] = ours_hash
                # If we deleted it, don't include
                continue
            
            # Case 3: File only changed in their branch
            if base_hash == ours_hash and theirs_hash != base_hash:
                if theirs_hash:
                    merged_files[path] = theirs_hash
                # If they deleted it, don't include
                continue
            
            # Case 4: File changed in both branches - potential conflict
            # Try to auto-merge if possible
            base_content = self._get_blob_content(base_hash) if base_hash else None
            ours_content = self._get_blob_content(ours_hash) if ours_hash else None
            theirs_content = self._get_blob_content(theirs_hash) if theirs_hash else None
            
            # Try line-based merge first
            merged_content = self._try_auto_merge(base_content, ours_content, theirs_content)
            
            # If line-based failed and we have an auto_strategy, try strategy-based resolution
            if merged_content is None and auto_strategy:
                merged_content = self._resolve_with_strategy(
                    base_content, ours_content, theirs_content,
                    auto_strategy, ours_is_recent, theirs_branch
                )
            
            if merged_content is not None:
                # Auto-merge succeeded
                from lit.core.objects import Blob
                blob = Blob(merged_content)
                merged_hash = self.repo.write_object(blob)
                merged_files[path] = merged_hash
            else:
                # Conflict detected
                conflicts.append(MergeConflict(
                    path=path,
                    base_content=base_content,
                    ours_content=ours_content,
                    theirs_content=theirs_content
                ))
        
        return merged_files, conflicts
    
    def _get_blob_content(self, blob_hash: str) -> Optional[bytes]:
        """Get content of a blob."""
        try:
            blob = self.repo.read_object(blob_hash)
            return blob.data
        except:
            return None
    
    def _try_auto_merge(
        self,
        base_content: Optional[bytes],
        ours_content: Optional[bytes],
        theirs_content: Optional[bytes]
    ) -> Optional[bytes]:
        """
        Try to automatically merge content using line-based merge.
        
        Args:
            base_content: Content in base version
            ours_content: Content in our version
            theirs_content: Content in their version
            
        Returns:
            Merged content if successful, None if conflicts detected
        """
        # If any content is None (file added/deleted), can't auto-merge
        if base_content is None or ours_content is None or theirs_content is None:
            return None
        
        try:
            # Split into lines
            base_lines = base_content.decode('utf-8', errors='replace').splitlines(keepends=True)
            ours_lines = ours_content.decode('utf-8', errors='replace').splitlines(keepends=True)
            theirs_lines = theirs_content.decode('utf-8', errors='replace').splitlines(keepends=True)
            
            # Simple line-based merge
            # If changes are in different parts of file, we can merge
            # For now, just detect if they modified same lines
            
            if len(base_lines) != len(ours_lines) or len(base_lines) != len(theirs_lines):
                # Different number of lines - more complex merge needed
                return None
            
            merged_lines = []
            for i, base_line in enumerate(base_lines):
                ours_line = ours_lines[i]
                theirs_line = theirs_lines[i]
                
                if ours_line == theirs_line:
                    # Same in both
                    merged_lines.append(ours_line)
                elif ours_line == base_line:
                    # Only changed in theirs
                    merged_lines.append(theirs_line)
                elif theirs_line == base_line:
                    # Only changed in ours
                    merged_lines.append(ours_line)
                else:
                    # Both changed same line - conflict
                    return None
            
            return ''.join(merged_lines).encode('utf-8')
        
        except:
            # Any error in merge logic - report conflict
            return None
    
    def _resolve_with_strategy(
        self,
        base_content: Optional[bytes],
        ours_content: Optional[bytes],
        theirs_content: Optional[bytes],
        strategy: str,
        ours_is_recent: bool = True,
        theirs_branch: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Resolve a conflict using the specified strategy.
        
        Args:
            base_content: Content in base version
            ours_content: Content in our version
            theirs_content: Content in their version
            strategy: Resolution strategy ('recent', 'ours', 'theirs', 'union')
            ours_is_recent: Whether ours is the more recent commit
            theirs_branch: Name of the branch being merged in (for messages)
            
        Returns:
            Resolved content
        """
        if strategy == 'ours':
            # Always take our version
            return ours_content if ours_content is not None else b''
        
        elif strategy == 'theirs':
            # Always take their version
            return theirs_content if theirs_content is not None else b''
        
        elif strategy == 'recent':
            # Take the more recent version
            if ours_is_recent:
                return ours_content if ours_content is not None else b''
            else:
                return theirs_content if theirs_content is not None else b''
        
        elif strategy == 'union':
            # Include both versions with a separator
            result = []
            
            if ours_content:
                result.append(ours_content)
                # Ensure newline between versions
                if not ours_content.endswith(b'\n'):
                    result.append(b'\n')
            
            if theirs_content:
                # Add separator comment with branch name
                branch_name = theirs_branch or 'other branch'
                result.append(f'\n# === merged from {branch_name} ===\n\n'.encode())
                result.append(theirs_content)
            
            return b''.join(result) if result else b''
        
        # Unknown strategy - return None to trigger conflict
        return None
    
    def generate_conflict_markers(
        self,
        path: str,
        ours_content: Optional[bytes],
        theirs_content: Optional[bytes],
        base_content: Optional[bytes] = None
    ) -> bytes:
        """
        Generate conflict markers for a file.
        
        Args:
            path: File path
            ours_content: Content from our branch
            theirs_content: Content from their branch
            base_content: Content from base (optional)
            
        Returns:
            File content with conflict markers
        """
        result = []
        
        # Header
        result.append(f"<<<<<<< HEAD\n".encode('utf-8'))
        
        # Our version
        if ours_content:
            result.append(ours_content)
            if not ours_content.endswith(b'\n'):
                result.append(b'\n')
        
        # Separator
        result.append(f"=======\n".encode('utf-8'))
        
        # Their version
        if theirs_content:
            result.append(theirs_content)
            if not theirs_content.endswith(b'\n'):
                result.append(b'\n')
        
        # Footer
        result.append(f">>>>>>> {path}\n".encode('utf-8'))
        
        return b''.join(result)
    
    def write_conflicts_to_working_tree(self, conflicts: List[MergeConflict]) -> None:
        """
        Write conflict markers to working tree files.
        
        Args:
            conflicts: List of merge conflicts
        """
        for conflict in conflicts:
            file_path = self.repo.work_tree / conflict.path
            
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Generate and write conflict markers
            conflicted_content = self.generate_conflict_markers(
                conflict.path,
                conflict.ours_content,
                conflict.theirs_content,
                conflict.base_content
            )
            
            file_path.write_bytes(conflicted_content)
    
    def save_merge_state(self, theirs_hash: str, conflicts: List[MergeConflict]) -> None:
        """
        Save merge state for later resolution or abort.
        
        Creates MERGE_HEAD and MERGE_MODE files to track ongoing merge.
        
        Args:
            theirs_hash: Hash of commit being merged
            conflicts: List of conflicts
        """
        # Write MERGE_HEAD
        merge_head_file = self.repo.lit_dir / 'MERGE_HEAD'
        merge_head_file.write_text(theirs_hash + '\n')
        
        # Write MERGE_MODE
        merge_mode_file = self.repo.lit_dir / 'MERGE_MODE'
        merge_mode_file.write_text('merge\n')
        
        # Write MERGE_MSG with conflict info
        merge_msg_file = self.repo.lit_dir / 'MERGE_MSG'
        msg_lines = [
            f"Merge conflicts detected\n",
            f"\n",
            f"Conflicts:\n"
        ]
        for conflict in conflicts:
            msg_lines.append(f"\t{conflict.path}\n")
        merge_msg_file.write_text(''.join(msg_lines))
    
    def clear_merge_state(self) -> None:
        """Clear merge state files."""
        merge_head = self.repo.lit_dir / 'MERGE_HEAD'
        merge_mode = self.repo.lit_dir / 'MERGE_MODE'
        merge_msg = self.repo.lit_dir / 'MERGE_MSG'
        
        if merge_head.exists():
            merge_head.unlink()
        if merge_mode.exists():
            merge_mode.unlink()
        if merge_msg.exists():
            merge_msg.unlink()
    
    def is_merge_in_progress(self) -> bool:
        """Check if a merge is in progress."""
        merge_head = self.repo.lit_dir / 'MERGE_HEAD'
        return merge_head.exists()
    
    def get_merge_head(self) -> Optional[str]:
        """Get the commit hash being merged (from MERGE_HEAD)."""
        merge_head = self.repo.lit_dir / 'MERGE_HEAD'
        if merge_head.exists():
            return merge_head.read_text().strip()
        return None
    
    def abort_merge(self) -> bool:
        """
        Abort an in-progress merge.
        
        Resets working tree and index to HEAD state, then clears merge state.
        
        Returns:
            True if merge was aborted, False if no merge in progress
        """
        if not self.is_merge_in_progress():
            return False
        
        # Get current HEAD commit
        current_hash = self.repo.refs.resolve_head()
        if not current_hash:
            return False
        
        # Reset working tree and index to HEAD
        from lit.core.objects import Commit
        commit = self.repo.read_object(current_hash)
        if isinstance(commit, Commit):
            # Use the remote manager's checkout function to restore working tree
            self.repo.remote._checkout_commit(self.repo, commit)
        
        # Clear merge state
        self.clear_merge_state()
        
        return True
    
    def merge(self, target_branch: str, allow_fast_forward: bool = True, auto_strategy: Optional[str] = None) -> MergeResult:
        """
        Merge target branch into current branch.
        
        Args:
            target_branch: Name of branch to merge
            allow_fast_forward: Whether to allow fast-forward merges
            auto_strategy: Strategy for auto-resolving conflicts:
                - None: No auto-resolution (report conflicts)
                - 'recent': Most recent commit wins (default for --auto)
                - 'ours': Always take our version
                - 'theirs': Always take their version
                - 'union': Include both versions
            
        Returns:
            MergeResult with status and any conflicts
        """
        # Get current HEAD
        current_hash = self.repo.refs.resolve_head()
        if not current_hash:
            return MergeResult(
                success=False,
                conflicts=[],
                message="No commits on current branch"
            )
        
        # Get target commit - check local branches first, then remote tracking branches
        target_hash = self.repo.refs.read_ref(f"refs/heads/{target_branch}")
        if not target_hash:
            # Try remote tracking branch (e.g., origin/feature-branch)
            if '/' in target_branch:
                target_hash = self.repo.refs.read_ref(f"refs/remotes/{target_branch}")
        if not target_hash:
            return MergeResult(
                success=False,
                conflicts=[],
                message=f"Branch '{target_branch}' not found"
            )
        
        # Check if already up to date
        if current_hash == target_hash:
            return MergeResult(
                success=True,
                conflicts=[],
                message="Already up to date"
            )
        
        # Check for fast-forward
        if allow_fast_forward and self.can_fast_forward(current_hash, target_hash):
            return self.fast_forward(target_hash)
        
        # Find merge base
        merge_base = self.find_merge_base(current_hash, target_hash)
        if not merge_base:
            return MergeResult(
                success=False,
                conflicts=[],
                message="No common ancestor found"
            )
        
        # Perform three-way merge
        return self.three_way_merge(merge_base, current_hash, target_hash, auto_strategy=auto_strategy, theirs_branch=target_branch)
