"""Reference management for Lit VCS."""

from pathlib import Path
from typing import Optional, List, Tuple
from lit.core.objects import Commit


class RefManager:
    """
    Manages Git references (branches, tags, HEAD).
    
    Handles:
    - Symbolic references (HEAD pointing to branch)
    - Direct references (detached HEAD)
    - Branch references (refs/heads/*)
    - Tag references (refs/tags/*)
    - Reference resolution and validation
    """
    
    def __init__(self, repo):
        """
        Initialize reference manager.
        
        Args:
            repo: Repository instance
        """
        self.repo = repo
        self.lit_dir = repo.lit_dir
        self.refs_dir = self.lit_dir / 'refs'
        self.heads_dir = self.refs_dir / 'heads'
        self.tags_dir = self.refs_dir / 'tags'
        self.head_file = self.lit_dir / 'HEAD'
    
    def read_ref(self, ref_name: str) -> Optional[str]:
        """
        Read a reference and return its commit hash.
        
        Args:
            ref_name: Reference name (e.g., 'refs/heads/main', 'HEAD', 'main')
        
        Returns:
            Commit hash or None if reference doesn't exist
        """
        # Handle HEAD specially
        if ref_name == 'HEAD':
            return self.resolve_head()
        
        # Try as full reference path
        ref_path = self.lit_dir / ref_name
        if ref_path.exists() and ref_path.is_file():
            content = ref_path.read_text().strip()
            # Check if it's a symbolic reference
            if content.startswith('ref: '):
                return self.read_ref(content[5:])
            return content
        
        # Try as branch name (refs/heads/<name>)
        branch_path = self.heads_dir / ref_name
        if branch_path.exists() and branch_path.is_file():
            return branch_path.read_text().strip()
        
        # Try as tag name (refs/tags/<name>)
        tag_path = self.tags_dir / ref_name
        if tag_path.exists() and tag_path.is_file():
            return tag_path.read_text().strip()
        
        return None
    
    def write_ref(self, ref_name: str, commit_hash: str, create_only: bool = False) -> bool:
        """
        Write a reference to point to a commit.
        
        Args:
            ref_name: Reference name (e.g., 'refs/heads/main')
            commit_hash: Commit hash to point to
            create_only: Only create if doesn't exist
        
        Returns:
            True if successful, False otherwise
        """
        ref_path = self.lit_dir / ref_name
        
        # Check if reference exists and create_only is set
        if create_only and ref_path.exists():
            return False
        
        # Create parent directories
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Validate commit exists
        try:
            obj = self.repo.read_object(commit_hash)
            if not isinstance(obj, Commit):
                return False
        except:
            return False
        
        # Write reference
        ref_path.write_text(commit_hash + '\n')
        return True
    
    def delete_ref(self, ref_name: str) -> bool:
        """
        Delete a reference.
        
        Args:
            ref_name: Reference name
        
        Returns:
            True if deleted, False if not found
        """
        # Determine full path
        if ref_name.startswith('refs/'):
            ref_path = self.lit_dir / ref_name
        else:
            # Try as branch
            ref_path = self.heads_dir / ref_name
            if not ref_path.exists():
                # Try as tag
                ref_path = self.tags_dir / ref_name
        
        if ref_path.exists():
            ref_path.unlink()
            return True
        
        return False
    
    def resolve_head(self) -> Optional[str]:
        """
        Resolve HEAD to a commit hash.
        
        Returns:
            Commit hash or None if HEAD doesn't exist
        """
        if not self.head_file.exists():
            return None
        
        content = self.head_file.read_text().strip()
        
        # Check if symbolic reference
        if content.startswith('ref: '):
            ref_name = content[5:]
            return self.read_ref(ref_name)
        
        # Direct hash (detached HEAD)
        return content
    
    def get_current_branch(self) -> Optional[str]:
        """
        Get the current branch name.
        
        Returns:
            Branch name or None if in detached HEAD state
        """
        if not self.head_file.exists():
            return None
        
        content = self.head_file.read_text().strip()
        
        if content.startswith('ref: refs/heads/'):
            return content[16:]
        
        # Detached HEAD
        return None
    
    def is_detached_head(self) -> bool:
        """
        Check if HEAD is in detached state.
        
        Returns:
            True if detached, False if on a branch
        """
        if not self.head_file.exists():
            return False
        
        content = self.head_file.read_text().strip()
        return not content.startswith('ref: ')
    
    def set_head(self, target: str, symbolic: bool = True) -> bool:
        """
        Set HEAD to point to a branch or commit.
        
        Args:
            target: Branch name (if symbolic) or commit hash (if direct)
            symbolic: If True, create symbolic reference; if False, direct reference
        
        Returns:
            True if successful
        """
        if symbolic:
            # Create symbolic reference to branch
            if not target.startswith('refs/heads/'):
                target = f'refs/heads/{target}'
            
            # Verify branch exists
            branch_path = self.lit_dir / target
            if not branch_path.exists():
                return False
            
            self.head_file.write_text(f'ref: {target}\n')
        else:
            # Direct reference (detached HEAD)
            # Validate commit exists
            try:
                obj = self.repo.read_object(target)
                if not isinstance(obj, Commit):
                    return False
            except:
                return False
            
            self.head_file.write_text(target + '\n')
        
        return True
    
    def list_branches(self) -> List[Tuple[str, str]]:
        """
        List all branches.
        
        Returns:
            List of (branch_name, commit_hash) tuples
        """
        if not self.heads_dir.exists():
            return []
        
        branches = []
        for branch_file in self.heads_dir.rglob('*'):
            if branch_file.is_file():
                # Get relative path from heads_dir
                branch_name = str(branch_file.relative_to(self.heads_dir))
                commit_hash = branch_file.read_text().strip()
                branches.append((branch_name, commit_hash))
        
        return sorted(branches, key=lambda x: x[0])
    
    def list_tags(self) -> List[Tuple[str, str]]:
        """
        List all tags.
        
        Returns:
            List of (tag_name, commit_hash) tuples
        """
        if not self.tags_dir.exists():
            return []
        
        tags = []
        for tag_file in self.tags_dir.rglob('*'):
            if tag_file.is_file():
                tag_name = str(tag_file.relative_to(self.tags_dir))
                commit_hash = tag_file.read_text().strip()
                tags.append((tag_name, commit_hash))
        
        return sorted(tags, key=lambda x: x[0])
    
    def create_branch(self, branch_name: str, commit_hash: str) -> bool:
        """
        Create a new branch.
        
        Args:
            branch_name: Branch name
            commit_hash: Commit hash to point to
        
        Returns:
            True if created, False if already exists
        """
        ref_name = f'refs/heads/{branch_name}'
        return self.write_ref(ref_name, commit_hash, create_only=True)
    
    def create_tag(self, tag_name: str, commit_hash: str) -> bool:
        """
        Create a new tag.
        
        Args:
            tag_name: Tag name
            commit_hash: Commit hash to point to
        
        Returns:
            True if created, False if already exists
        """
        ref_name = f'refs/tags/{tag_name}'
        return self.write_ref(ref_name, commit_hash, create_only=True)
    
    def update_branch(self, branch_name: str, commit_hash: str) -> bool:
        """
        Update an existing branch to point to a new commit.
        
        Args:
            branch_name: Branch name
            commit_hash: New commit hash
        
        Returns:
            True if successful
        """
        ref_name = f'refs/heads/{branch_name}'
        return self.write_ref(ref_name, commit_hash, create_only=False)
    
    def delete_branch(self, branch_name: str) -> bool:
        """
        Delete a branch.
        
        Args:
            branch_name: Branch name
        
        Returns:
            True if deleted, False if not found
        """
        # Don't delete current branch
        current = self.get_current_branch()
        if current == branch_name:
            return False
        
        ref_name = f'refs/heads/{branch_name}'
        return self.delete_ref(ref_name)
    
    def delete_tag(self, tag_name: str) -> bool:
        """
        Delete a tag.
        
        Args:
            tag_name: Tag name
        
        Returns:
            True if deleted, False if not found
        """
        ref_name = f'refs/tags/{tag_name}'
        return self.delete_ref(ref_name)
    
    def resolve_reference(self, ref: str) -> Optional[str]:
        """
        Resolve any reference (branch, tag, HEAD, hash) to a commit hash.
        
        Args:
            ref: Reference string (e.g., 'HEAD', 'main', 'v1.0', commit hash)
        
        Returns:
            Commit hash or None if reference can't be resolved
        """
        # Try as direct hash (40 hex chars)
        if len(ref) >= 7 and all(c in '0123456789abcdef' for c in ref.lower()):
            # Could be a hash or partial hash
            if len(ref) == 40:
                # Full hash
                try:
                    obj = self.repo.read_object(ref)
                    if isinstance(obj, Commit):
                        return ref
                except:
                    pass
            else:
                # Partial hash - try to find full hash
                from lit.cli.commands.log import find_commit_by_prefix
                full_hash = find_commit_by_prefix(self.repo, ref)
                if full_hash:
                    return full_hash
        
        # Try as reference name
        return self.read_ref(ref)
    
    def get_ref_info(self, ref: str) -> dict:
        """
        Get detailed information about a reference.
        
        Args:
            ref: Reference name
        
        Returns:
            Dictionary with reference information
        """
        info = {
            'exists': False,
            'type': None,
            'target': None,
            'symbolic': False,
            'symbolic_target': None
        }
        
        if ref == 'HEAD':
            if self.head_file.exists():
                info['exists'] = True
                info['type'] = 'HEAD'
                content = self.head_file.read_text().strip()
                
                if content.startswith('ref: '):
                    info['symbolic'] = True
                    info['symbolic_target'] = content[5:]
                    info['target'] = self.read_ref(content[5:])
                else:
                    info['target'] = content
        else:
            # Check as branch
            branch_path = self.heads_dir / ref
            if branch_path.exists():
                info['exists'] = True
                info['type'] = 'branch'
                info['target'] = branch_path.read_text().strip()
            
            # Check as tag
            tag_path = self.tags_dir / ref
            if tag_path.exists():
                info['exists'] = True
                info['type'] = 'tag'
                info['target'] = tag_path.read_text().strip()
        
        return info
