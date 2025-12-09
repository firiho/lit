"""Cherry-pick command for Lit VCS."""

import click
import time
from pathlib import Path
from colorama import Fore, Style

from lit.core.repository import Repository
from lit.core.objects import Commit, Blob, Tree
from lit.core.index import Index
from lit.operations.merge import MergeEngine
from lit.cli.output import error, success, info, warning


def get_commit_changes(repo, commit_hash: str) -> dict:
    """
    Get the changes introduced by a commit.
    
    Compares the commit's tree to its parent's tree to get the diff.
    
    Args:
        repo: Repository instance
        commit_hash: Commit to get changes from
        
    Returns:
        Dict with 'added', 'modified', 'deleted' file paths and their content
    """
    commit = repo.read_object(commit_hash)
    if not isinstance(commit, Commit):
        return {}
    
    # Get commit tree files
    commit_files = get_tree_files_recursive(repo, commit.tree)
    
    # Get parent tree files (if has parent)
    if commit.parents:
        parent = repo.read_object(commit.parents[0])
        if isinstance(parent, Commit):
            parent_files = get_tree_files_recursive(repo, parent.tree)
        else:
            parent_files = {}
    else:
        parent_files = {}
    
    changes = {
        'added': {},      # path -> blob_hash
        'modified': {},   # path -> blob_hash
        'deleted': set()  # path
    }
    
    # Find added and modified files
    for path, blob_hash in commit_files.items():
        if path not in parent_files:
            changes['added'][path] = blob_hash
        elif parent_files[path] != blob_hash:
            changes['modified'][path] = blob_hash
    
    # Find deleted files
    for path in parent_files:
        if path not in commit_files:
            changes['deleted'].add(path)
    
    return changes


def get_tree_files_recursive(repo, tree_hash: str, prefix: str = "") -> dict:
    """Get all files from a tree recursively."""
    files = {}
    tree = repo.read_object(tree_hash)
    
    if not tree:
        return files
    
    for entry in tree.entries:
        path = f"{prefix}/{entry.name}" if prefix else entry.name
        if entry.type == 'blob':
            files[path] = entry.hash
        elif entry.type == 'tree':
            files.update(get_tree_files_recursive(repo, entry.hash, path))
    
    return files


def apply_changes_to_workdir(repo, changes: dict) -> list:
    """
    Apply commit changes to working directory and index.
    
    Returns list of conflict paths if any.
    """
    conflicts = []
    index = Index()
    if repo.index_file.exists():
        index.read(str(repo.index_file))
    
    # Apply added files
    for path, blob_hash in changes['added'].items():
        blob = repo.read_object(blob_hash)
        if blob:
            full_path = repo.work_tree / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_bytes(blob.data)
            
            # Add to index
            stat = full_path.stat()
            index.add_entry(
                path=path,
                sha1=blob_hash,
                mode=stat.st_mode,
                size=stat.st_size,
                mtime=int(stat.st_mtime),
                ctime=int(stat.st_ctime)
            )
    
    # Apply modified files
    for path, blob_hash in changes['modified'].items():
        full_path = repo.work_tree / path
        
        # Check for conflicts with uncommitted changes
        if full_path.exists():
            current_content = full_path.read_bytes()
            
            # Get expected content from index
            entry = index.get_entry(path)
            if entry:
                expected_blob = repo.read_object(entry.sha1)
                if expected_blob and expected_blob.data != current_content:
                    # Working tree has uncommitted changes - conflict
                    conflicts.append(path)
                    continue
        
        blob = repo.read_object(blob_hash)
        if blob:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_bytes(blob.data)
            
            # Update index
            stat = full_path.stat()
            index.add_entry(
                path=path,
                sha1=blob_hash,
                mode=stat.st_mode,
                size=stat.st_size,
                mtime=int(stat.st_mtime),
                ctime=int(stat.st_ctime)
            )
    
    # Apply deleted files
    for path in changes['deleted']:
        full_path = repo.work_tree / path
        if full_path.exists():
            full_path.unlink()
        index.remove_entry(path)
    
    # Write index
    index.write(str(repo.index_file))
    
    return conflicts


def create_cherry_pick_commit(repo, original_commit: Commit, edit_message: bool = False, message: str = None) -> str:
    """
    Create a new commit with same message as original.
    
    Returns the new commit hash.
    """
    from lit.core.objects import Tree
    
    # Build tree from index
    index = Index()
    index.read(str(repo.index_file))
    
    # Build tree from index entries
    root = {}
    for path, entry in index.entries.items():
        parts = path.split('/')
        current = root
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        filename = parts[-1]
        current[filename] = (entry.sha1, entry.mode)
    
    tree_hash = write_tree_recursive(repo, root)
    
    # Get HEAD as parent
    head = repo.refs.resolve_head()
    
    # Create commit
    new_commit = Commit()
    new_commit.tree = tree_hash
    new_commit.parents = [head] if head else []
    new_commit.author = original_commit.author
    new_commit.author_time = int(time.time())
    new_commit.author_timezone = original_commit.author_timezone
    new_commit.committer = original_commit.committer
    new_commit.committer_time = int(time.time())
    new_commit.committer_timezone = original_commit.committer_timezone
    
    # Use custom message or original
    if message:
        new_commit.message = message
    else:
        new_commit.message = original_commit.message
    
    # Write commit
    commit_hash = repo.write_object(new_commit)
    
    # Update HEAD
    head_content = (repo.lit_dir / 'HEAD').read_text().strip()
    if head_content.startswith('ref: '):
        # Update branch
        branch_ref = head_content[5:]
        ref_path = repo.lit_dir / branch_ref
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        ref_path.write_text(commit_hash)
    else:
        # Detached HEAD
        (repo.lit_dir / 'HEAD').write_text(commit_hash)
    
    return commit_hash


def write_tree_recursive(repo, node: dict) -> str:
    """Recursively write tree objects."""
    tree = Tree()
    
    for name, value in sorted(node.items()):
        if isinstance(value, tuple):
            sha1, mode = value
            if mode & 0o111:
                mode_str = '100755'
            else:
                mode_str = '100644'
            tree.add_entry(mode_str, 'blob', sha1, name)
        else:
            subtree_hash = write_tree_recursive(repo, value)
            tree.add_entry('040000', 'tree', subtree_hash, name)
    
    return repo.write_object(tree)


def save_cherry_pick_state(repo, commit_hash: str):
    """Save cherry-pick state for conflict resolution."""
    (repo.lit_dir / 'CHERRY_PICK_HEAD').write_text(commit_hash)


def clear_cherry_pick_state(repo):
    """Clear cherry-pick state files."""
    cherry_pick_head = repo.lit_dir / 'CHERRY_PICK_HEAD'
    if cherry_pick_head.exists():
        cherry_pick_head.unlink()


def is_cherry_pick_in_progress(repo) -> bool:
    """Check if a cherry-pick is in progress."""
    return (repo.lit_dir / 'CHERRY_PICK_HEAD').exists()


def get_cherry_pick_head(repo) -> str:
    """Get the commit being cherry-picked."""
    cherry_pick_head = repo.lit_dir / 'CHERRY_PICK_HEAD'
    if cherry_pick_head.exists():
        return cherry_pick_head.read_text().strip()
    return None


@click.command('cherry-pick')
@click.argument('commit', required=False)
@click.option('--continue', 'continue_pick', is_flag=True, help='Continue after resolving conflicts')
@click.option('--abort', 'abort_pick', is_flag=True, help='Abort cherry-pick operation')
@click.option('-m', '--message', help='Use custom commit message')
@click.option('-n', '--no-commit', is_flag=True, help='Apply changes without committing')
def cherry_pick_cmd(commit, continue_pick, abort_pick, message, no_commit):
    """Apply changes from a specific commit.
    
    Cherry-pick takes the changes introduced by an existing commit and
    applies them to the current branch as a new commit.
    
    Examples:
        lit cherry-pick abc1234     Apply commit abc1234
        lit cherry-pick HEAD~2      Apply the commit 2 before HEAD
        lit cherry-pick --continue  Continue after resolving conflicts
        lit cherry-pick --abort     Cancel cherry-pick operation
    """
    try:
        repo = Repository.find_repository()
        if not repo:
            click.echo(error("Not a lit repository"))
            return
        
        # Handle --abort
        if abort_pick:
            if not is_cherry_pick_in_progress(repo):
                click.echo(error("No cherry-pick in progress"))
                return
            
            # Reset to HEAD
            head = repo.refs.resolve_head()
            if head:
                head_commit = repo.read_object(head)
                if head_commit:
                    # Restore working tree and index from HEAD
                    tree_files = get_tree_files_recursive(repo, head_commit.tree)
                    index = Index()
                    
                    for path, blob_hash in tree_files.items():
                        blob = repo.read_object(blob_hash)
                        if blob:
                            full_path = repo.work_tree / path
                            full_path.parent.mkdir(parents=True, exist_ok=True)
                            full_path.write_bytes(blob.data)
                            
                            stat = full_path.stat()
                            index.add_entry(
                                path=path,
                                sha1=blob_hash,
                                mode=stat.st_mode,
                                size=stat.st_size,
                                mtime=int(stat.st_mtime),
                                ctime=int(stat.st_ctime)
                            )
                    
                    index.write(str(repo.index_file))
            
            clear_cherry_pick_state(repo)
            click.echo(success("Cherry-pick aborted"))
            return
        
        # Handle --continue
        if continue_pick:
            if not is_cherry_pick_in_progress(repo):
                click.echo(error("No cherry-pick in progress"))
                return
            
            original_hash = get_cherry_pick_head(repo)
            original_commit = repo.read_object(original_hash)
            
            if not isinstance(original_commit, Commit):
                click.echo(error("Invalid cherry-pick state"))
                clear_cherry_pick_state(repo)
                return
            
            # Create the commit
            new_hash = create_cherry_pick_commit(repo, original_commit, message=message)
            clear_cherry_pick_state(repo)
            
            click.echo(success(f"Cherry-pick completed: {new_hash[:7]}"))
            click.echo(info(f"  {original_commit.message.split(chr(10))[0]}"))
            return
        
        # Regular cherry-pick
        if not commit:
            click.echo(error("No commit specified"))
            click.echo(info("Usage: lit cherry-pick <commit>"))
            return
        
        if is_cherry_pick_in_progress(repo):
            click.echo(error("Cherry-pick already in progress"))
            click.echo(info("Use 'lit cherry-pick --continue' or 'lit cherry-pick --abort'"))
            return
        
        # Resolve commit reference
        commit_hash = resolve_commit_ref(repo, commit)
        if not commit_hash:
            click.echo(error(f"Unknown commit: {commit}"))
            return
        
        target_commit = repo.read_object(commit_hash)
        if not isinstance(target_commit, Commit):
            click.echo(error(f"Not a commit: {commit}"))
            return
        
        # Get changes from commit
        changes = get_commit_changes(repo, commit_hash)
        
        if not changes['added'] and not changes['modified'] and not changes['deleted']:
            click.echo(info("Nothing to cherry-pick (empty commit)"))
            return
        
        # Apply changes
        conflicts = apply_changes_to_workdir(repo, changes)
        
        if conflicts:
            # Save state for --continue
            save_cherry_pick_state(repo, commit_hash)
            
            click.echo(warning(f"Cherry-pick stopped due to conflicts"))
            click.echo(info("Conflicts in:"))
            for path in conflicts:
                click.echo(f"  {Fore.RED}{path}{Style.RESET_ALL}")
            click.echo()
            click.echo(info("Resolve conflicts and run 'lit cherry-pick --continue'"))
            click.echo(info("Or run 'lit cherry-pick --abort' to cancel"))
            return
        
        if no_commit:
            click.echo(success("Changes applied to working directory"))
            click.echo(info(f"  From: {commit_hash[:7]} {target_commit.message.split(chr(10))[0]}"))
            return
        
        # Create commit
        new_hash = create_cherry_pick_commit(repo, target_commit, message=message)
        
        click.echo(success(f"Cherry-picked: {commit_hash[:7]} → {new_hash[:7]}"))
        click.echo(info(f"  {target_commit.message.split(chr(10))[0]}"))
        
    except Exception as e:
        click.echo(error(f"Cherry-pick failed: {e}"))


def resolve_commit_ref(repo, ref: str) -> str:
    """
    Resolve a commit reference to a hash.
    
    Supports:
        - Full commit hash
        - Short commit hash
        - HEAD, HEAD~N, HEAD^
        - branch~N, branch^
        - Branch names
        - Tag names
    """
    # Handle ~N and ^ suffixes for any ref
    base_ref = ref
    ancestor_count = 0
    
    if '~' in ref:
        parts = ref.split('~')
        base_ref = parts[0]
        try:
            ancestor_count = int(parts[1]) if len(parts) > 1 and parts[1] else 1
        except ValueError:
            return None
    elif ref.endswith('^'):
        base_ref = ref[:-1]
        ancestor_count = 1
    
    # Resolve base ref
    if base_ref == 'HEAD':
        base_hash = repo.refs.resolve_head()
    else:
        # Try as branch/tag first
        base_hash = repo.refs.read_ref(base_ref)
        
        # If not found, try as partial/full hash
        if not base_hash:
            objects_dir = repo.lit_dir / 'objects'
            if len(base_ref) >= 4:
                for subdir in objects_dir.iterdir():
                    if subdir.is_dir() and subdir.name.startswith(base_ref[:2]):
                        for obj_file in subdir.iterdir():
                            full_hash = subdir.name + obj_file.name
                            if full_hash.startswith(base_ref):
                                base_hash = full_hash
                                break
                        if base_hash:
                            break
            
            # Try as full hash
            if not base_hash and len(base_ref) == 40:
                prefix = base_ref[:2]
                suffix = base_ref[2:]
                obj_path = objects_dir / prefix / suffix
                if obj_path.exists():
                    base_hash = base_ref
    
    if not base_hash:
        return None
    
    # Navigate to ancestor if needed
    current = base_hash
    for _ in range(ancestor_count):
        commit = repo.read_object(current)
        if not isinstance(commit, Commit) or not commit.parents:
            return None
        current = commit.parents[0]
    
    return current
