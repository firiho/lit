"""Remote repository operations for Lit VCS."""

import shutil
import configparser
from pathlib import Path
from typing import Optional, Dict, List
from .repository import Repository


class RemoteManager:
    """
    Manages remote repository operations.
    
    Currently supports local file system remotes (file://).
    Designed to be extended with HTTP/SSH protocols later.
    """
    
    def __init__(self, repo: Repository):
        """Initialize remote manager."""
        self.repo = repo
    
    def add_remote(self, name: str, url: str):
        """
        Add a remote repository.
        
        Args:
            name: Remote name (e.g., 'origin')
            url: Remote URL (currently supports file:// or local paths)
        """
        config = configparser.ConfigParser()
        if self.repo.config_file.exists():
            config.read(self.repo.config_file)
        
        section = f'remote "{name}"'
        if not config.has_section(section):
            config.add_section(section)
        
        config.set(section, 'url', url)
        config.set(section, 'fetch', f'+refs/heads/*:refs/remotes/{name}/*')
        
        with open(self.repo.config_file, 'w') as f:
            config.write(f)
    
    def list_remotes(self) -> Dict[str, str]:
        """
        List all configured remotes.
        
        Returns:
            Dict mapping remote names to URLs
        """
        config = configparser.ConfigParser()
        if not self.repo.config_file.exists():
            return {}
        
        config.read(self.repo.config_file)
        remotes = {}
        
        for section in config.sections():
            if section.startswith('remote "') and section.endswith('"'):
                name = section[8:-1]  # Extract name from 'remote "name"'
                url = config.get(section, 'url')
                remotes[name] = url
        
        return remotes
    
    def get_remote_url(self, name: str) -> Optional[str]:
        """Get URL for a remote."""
        remotes = self.list_remotes()
        return remotes.get(name)
    
    def remove_remote(self, name: str):
        """Remove a remote."""
        config = configparser.ConfigParser()
        if not self.repo.config_file.exists():
            return
        
        config.read(self.repo.config_file)
        section = f'remote "{name}"'
        
        if config.has_section(section):
            config.remove_section(section)
            with open(self.repo.config_file, 'w') as f:
                config.write(f)
    
    def _parse_url(self, url: str) -> tuple[str, str]:
        """
        Parse remote URL to determine protocol and path.
        
        Args:
            url: Remote URL
            
        Returns:
            Tuple of (protocol, path)
            
        Examples:
            file:///path/to/repo -> ('file', '/path/to/repo')
            /path/to/repo -> ('file', '/path/to/repo')
            https://github.com/user/repo.git -> ('https', 'github.com/user/repo.git')
        """
        if url.startswith('file://'):
            return ('file', url[7:])
        elif url.startswith('https://'):
            return ('https', url[8:])
        elif url.startswith('http://'):
            return ('http', url[7:])
        elif url.startswith('ssh://'):
            return ('ssh', url[6:])
        elif url.startswith('git@'):
            return ('ssh', url)
        else:
            # Assume local file path
            return ('file', url)
    
    def clone(self, source_url: str, dest_path: str, remote_name: str = 'origin', 
              bare: bool = False) -> Repository:
        """
        Clone a repository from a remote source.
        
        Args:
            source_url: URL or path to source repository
            dest_path: Destination path for cloned repository
            remote_name: Name for the remote (default: 'origin')
            bare: If True, create a bare repository (no working directory)
            
        Returns:
            Repository: The cloned repository
            
        Raises:
            Exception: If source doesn't exist or destination already exists
        """
        dest = Path(dest_path).resolve()
        
        if dest.exists():
            raise Exception(f"Destination already exists: {dest}")
        
        protocol, path = self._parse_url(source_url)
        
        if protocol == 'file':
            return self._clone_local(path, dest, remote_name, source_url, bare)
        else:
            raise NotImplementedError(
                f"Protocol '{protocol}' not yet implemented. "
                f"Currently only local file:// cloning is supported."
            )
    
    def _clone_local(self, source_path: str, dest_path: Path, 
                     remote_name: str, source_url: str, bare: bool = False) -> Repository:
        """Clone from a local file system repository."""
        source = Path(source_path).resolve()
        
        if not source.exists():
            raise Exception(f"Source repository not found: {source}")
        
        source_lit = source / '.lit'
        if not source_lit.exists():
            raise Exception(f"Not a valid lit repository: {source}")
        
        # Create destination directory
        dest_path.mkdir(parents=True)
        
        # Initialize new repository
        dest_repo = Repository(str(dest_path))
        dest_repo.init()
        
        # Copy all objects
        source_objects = source_lit / 'objects'
        dest_objects = dest_repo.objects_dir
        
        if source_objects.exists():
            for obj_dir in source_objects.iterdir():
                if obj_dir.is_dir() and len(obj_dir.name) == 2:
                    dest_obj_dir = dest_objects / obj_dir.name
                    dest_obj_dir.mkdir(exist_ok=True)
                    for obj_file in obj_dir.iterdir():
                        shutil.copy2(obj_file, dest_obj_dir / obj_file.name)
        
        # Copy all refs (branches and tags)
        source_refs = source_lit / 'refs'
        if source_refs.exists():
            # Copy branches
            source_heads = source_refs / 'heads'
            if source_heads.exists():
                for branch_file in source_heads.iterdir():
                    if branch_file.is_file():
                        if bare:
                            # For bare repos, copy branches directly to heads/
                            shutil.copy2(branch_file, dest_repo.heads_dir / branch_file.name)
                        else:
                            # For regular clones, copy to remotes/
                            remote_ref_dir = dest_repo.remotes_dir / remote_name
                            remote_ref_dir.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(branch_file, remote_ref_dir / branch_file.name)
            
            # Copy tags
            source_tags = source_refs / 'tags'
            if source_tags.exists():
                for tag_file in source_tags.iterdir():
                    if tag_file.is_file():
                        shutil.copy2(tag_file, dest_repo.tags_dir / tag_file.name)
        
        if bare:
            # For bare repos: just set HEAD to point to main branch
            # Don't add remote, don't checkout files
            source_head = source_lit / 'HEAD'
            if source_head.exists():
                head_content = source_head.read_text().strip()
                if head_content.startswith('ref: refs/heads/'):
                    # Copy the HEAD reference
                    dest_repo.head_file.write_text(head_content + '\n')
                else:
                    # Default to main
                    dest_repo.head_file.write_text('ref: refs/heads/main\n')
        else:
            # For regular clones: add remote and checkout
            # Add remote with absolute path
            # Store absolute path so push/pull work correctly
            absolute_source_url = str(source)
            dest_repo.remote.add_remote(remote_name, absolute_source_url)
            
            # Determine default branch (read from source's HEAD)
            source_head = source_lit / 'HEAD'
            if source_head.exists():
                head_content = source_head.read_text().strip()
                if head_content.startswith('ref: refs/heads/'):
                    default_branch = head_content[16:]
                    
                    # Get the commit hash for the default branch
                    remote_ref = dest_repo.remotes_dir / remote_name / default_branch
                    if remote_ref.exists():
                        commit_hash = remote_ref.read_text().strip()
                        
                        # Create local branch tracking remote
                        dest_repo.refs.write_ref(f'refs/heads/{default_branch}', commit_hash)
                        
                        # Update HEAD to point to the new branch
                        dest_repo.head_file.write_text(f'ref: refs/heads/{default_branch}\n')
                        
                        # Checkout the default branch
                        from .objects import Commit
                        commit = dest_repo.read_object(commit_hash)
                        if isinstance(commit, Commit):
                            self._checkout_commit(dest_repo, commit)
        
        return dest_repo
    
    def _checkout_commit(self, repo: Repository, commit):
        """Checkout a commit to the working directory."""
        from .objects import Tree, Blob
        from .index import Index
        
        # Clear working directory (except .lit)
        for item in repo.work_tree.iterdir():
            if item.name != '.lit':
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
        
        # Get tree and restore files
        tree = repo.read_object(commit.tree)
        if isinstance(tree, Tree):
            self._restore_tree(repo, tree, repo.work_tree)
        
        # Update index
        index = Index()
        self._index_tree(repo, tree, index, '')
        index.write(str(repo.index_file))
    
    def _restore_tree(self, repo: Repository, tree, path: Path):
        """Recursively restore tree to working directory."""
        from .objects import Tree, Blob
        
        for entry in tree.entries:
            entry_path = path / entry.name
            obj = repo.read_object(entry.hash)
            
            if isinstance(obj, Blob):
                entry_path.write_bytes(obj.data)
            elif isinstance(obj, Tree):
                entry_path.mkdir(exist_ok=True)
                self._restore_tree(repo, obj, entry_path)
    
    def _index_tree(self, repo: Repository, tree, index, prefix: str):
        """Recursively add tree entries to index."""
        from .objects import Tree, Blob
        
        for entry in tree.entries:
            path = f"{prefix}{entry.name}" if prefix else entry.name
            obj = repo.read_object(entry.hash)
            
            if isinstance(obj, Blob):
                # Get blob size and convert mode to int
                size = len(obj.data)
                mode = int(entry.mode, 8)  # Convert octal string to int
                index.add_entry(path, entry.hash, mode, size)
            elif isinstance(obj, Tree):
                self._index_tree(repo, obj, index, f"{path}/")
    
    def fetch(self, remote_name: str = 'origin', branch: Optional[str] = None):
        """
        Fetch updates from a remote repository.
        
        Downloads new commits and updates remote-tracking branches.
        Does NOT modify working directory or local branches.
        
        Args:
            remote_name: Name of remote to fetch from
            branch: Specific branch to fetch (None = fetch all)
            
        Raises:
            Exception: If remote not found or fetch fails
        """
        url = self.get_remote_url(remote_name)
        if not url:
            raise Exception(f"Remote '{remote_name}' not found")
        
        protocol, path = self._parse_url(url)
        
        if protocol == 'file':
            self._fetch_local(path, remote_name, branch)
        else:
            raise NotImplementedError(
                f"Protocol '{protocol}' not yet implemented. "
                f"Currently only local file:// fetching is supported."
            )
    
    def _fetch_local(self, source_path: str, remote_name: str, branch: Optional[str]):
        """Fetch from a local repository."""
        # Resolve path relative to repository root
        source = Path(source_path)
        if not source.is_absolute():
            source = (self.repo.work_tree / source_path).resolve()
        else:
            source = source.resolve()
        
        source_lit = source / '.lit'
        
        if not source_lit.exists():
            raise Exception(f"Not a valid lit repository: {source}")
        
        # Copy new objects
        source_objects = source_lit / 'objects'
        if source_objects.exists():
            for obj_dir in source_objects.iterdir():
                if obj_dir.is_dir() and len(obj_dir.name) == 2:
                    dest_obj_dir = self.repo.objects_dir / obj_dir.name
                    dest_obj_dir.mkdir(exist_ok=True)
                    for obj_file in obj_dir.iterdir():
                        dest_file = dest_obj_dir / obj_file.name
                        if not dest_file.exists():
                            shutil.copy2(obj_file, dest_file)
        
        # Update remote-tracking branches
        source_heads = source_lit / 'refs' / 'heads'
        if source_heads.exists():
            remote_ref_dir = self.repo.remotes_dir / remote_name
            remote_ref_dir.mkdir(parents=True, exist_ok=True)
            
            branches_to_fetch = [branch] if branch else [
                b.name for b in source_heads.iterdir() if b.is_file()
            ]
            
            for branch_name in branches_to_fetch:
                source_branch = source_heads / branch_name
                if source_branch.exists():
                    commit_hash = source_branch.read_text().strip()
                    dest_branch = remote_ref_dir / branch_name
                    dest_branch.write_text(commit_hash)
    
    def push(self, remote_name: str = 'origin', branch: Optional[str] = None):
        """
        Push local commits to a remote repository.
        
        Uploads new commits and updates remote branches.
        
        Args:
            remote_name: Name of remote to push to
            branch: Branch to push (None = push current branch)
            
        Raises:
            Exception: If remote not found, branch not found, or push fails
        """
        url = self.get_remote_url(remote_name)
        if not url:
            raise Exception(f"Remote '{remote_name}' not found")
        
        # Determine branch to push
        if not branch:
            head_content = self.repo.head_file.read_text().strip()
            if not head_content.startswith('ref: refs/heads/'):
                raise Exception("Cannot push from detached HEAD")
            branch = head_content[16:]
        
        # Check if branch exists locally
        local_ref = self.repo.heads_dir / branch
        if not local_ref.exists():
            raise Exception(f"Branch '{branch}' not found")
        
        protocol, path = self._parse_url(url)
        
        if protocol == 'file':
            self._push_local(path, branch)
        else:
            raise NotImplementedError(
                f"Protocol '{protocol}' not yet implemented. "
                f"Currently only local file:// pushing is supported."
            )
    
    def _push_local(self, dest_path: str, branch: str):
        """Push to a local repository."""
        # Resolve path relative to repository root
        dest = Path(dest_path)
        if not dest.is_absolute():
            dest = (self.repo.work_tree / dest_path).resolve()
        else:
            dest = dest.resolve()
        
        dest_lit = dest / '.lit'
        
        if not dest_lit.exists():
            raise Exception(f"Not a valid lit repository: {dest}")
        
        # Copy new objects
        dest_objects = dest_lit / 'objects'
        for obj_dir in self.repo.objects_dir.iterdir():
            if obj_dir.is_dir() and len(obj_dir.name) == 2:
                dest_obj_dir = dest_objects / obj_dir.name
                dest_obj_dir.mkdir(exist_ok=True)
                for obj_file in obj_dir.iterdir():
                    dest_file = dest_obj_dir / obj_file.name
                    if not dest_file.exists():
                        shutil.copy2(obj_file, dest_file)
        
        # Update branch reference
        local_ref = self.repo.heads_dir / branch
        commit_hash = local_ref.read_text().strip()
        
        dest_heads = dest_lit / 'refs' / 'heads'
        dest_heads.mkdir(parents=True, exist_ok=True)
        dest_branch = dest_heads / branch
        dest_branch.write_text(commit_hash)
