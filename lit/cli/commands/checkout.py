"""Checkout command - switch branches or restore files."""

import click
from pathlib import Path
from lit.core.repository import Repository
from lit.core.objects import Commit, Tree, Blob
from lit.core.index import Index
from lit.cli.output import success, error, info, warning
from colorama import Fore, Style


def get_current_branch(repo):
    """Get the name of the current branch."""
    head_file = repo.head_file
    
    if not head_file.exists():
        return None
    
    head_content = head_file.read_text().strip()
    
    if head_content.startswith('ref: refs/heads/'):
        return head_content[16:]
    
    return None


def branch_exists(repo, branch_name):
    """Check if a branch exists."""
    branch_file = repo.lit_dir / 'refs' / 'heads' / branch_name
    return branch_file.exists()


def get_tree_files(repo, tree, prefix=''):
    """Recursively get all files from tree."""
    files = {}
    
    if not tree:
        return files
    
    for entry in tree.entries:
        path = f"{prefix}{entry.name}" if prefix else entry.name
        
        if entry.type == 'blob':
            files[path] = entry.hash
        elif entry.type == 'tree':
            subtree = repo.read_object(entry.hash)
            if isinstance(subtree, Tree):
                subfiles = get_tree_files(repo, subtree, f"{path}/")
                files.update(subfiles)
    
    return files


def checkout_tree(repo, tree_hash):
    """
    Check out files from a tree into working directory.
    Updates index to match the tree.
    """
    tree = repo.read_object(tree_hash)
    if not isinstance(tree, Tree):
        raise ValueError("Not a valid tree")
    
    # Get all files from tree
    tree_files = get_tree_files(repo, tree)
    
    # Get current files in working directory
    work_tree = repo.work_tree
    existing_files = set()
    for path in work_tree.rglob('*'):
        if path.is_file():
            rel_path = path.relative_to(work_tree)
            if not any(part.startswith('.') for part in rel_path.parts):
                existing_files.add(str(rel_path))
    
    # Remove files not in the new tree
    for file_path in existing_files:
        if file_path not in tree_files:
            full_path = work_tree / file_path
            try:
                full_path.unlink()
                click.echo(info(f"Removed: {file_path}"))
            except:
                pass
    
    # Write all files from tree
    index = Index()
    for file_path, blob_hash in tree_files.items():
        full_path = work_tree / file_path
        
        # Create directory if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read blob and write to file
        blob = repo.read_object(blob_hash)
        if isinstance(blob, Blob):
            full_path.write_bytes(blob.data)
            
            # Add to index (add_file expects repo as first arg)
            index.add_file(repo, str(full_path))
    
    # Write index
    index_file = repo.index_file
    index.write(str(index_file))
    
    return len(tree_files)


def checkout_branch(repo, branch_name, create=False):
    """Switch to a branch."""
    # Check if branch exists
    if not branch_exists(repo, branch_name):
        if create:
            # Create branch from current HEAD
            from lit.cli.commands.branch import create_branch
            create_branch(repo, branch_name)
            click.echo(success(f"Created new branch '{branch_name}'"))
        else:
            click.echo(error(f"Branch '{branch_name}' not found"))
            click.echo(info(f"Use 'lit checkout -b {branch_name}' to create it"))
            raise click.Abort()
    
    # Check if already on this branch
    current_branch = get_current_branch(repo)
    if current_branch == branch_name:
        click.echo(info(f"Already on '{branch_name}'"))
        return
    
    # Get commit hash for the branch
    branch_file = repo.lit_dir / 'refs' / 'heads' / branch_name
    commit_hash = branch_file.read_text().strip()
    
    # Read commit
    try:
        commit = repo.read_object(commit_hash)
        if not isinstance(commit, Commit):
            click.echo(error(f"Invalid commit for branch '{branch_name}'"))
            raise click.Abort()
    except:
        click.echo(error(f"Cannot read commit for branch '{branch_name}'"))
        raise click.Abort()
    
    # TODO: Check for uncommitted changes and warn/error
    
    # Checkout the tree
    try:
        file_count = checkout_tree(repo, commit.tree)
    except Exception as e:
        click.echo(error(f"Failed to checkout tree: {e}"))
        raise click.Abort()
    
    # Update HEAD to point to the branch
    head_file = repo.head_file
    head_file.write_text(f"ref: refs/heads/{branch_name}\n")
    
    return file_count


def find_remote_tracking_branch(repo, branch_name):
    """
    Check if a remote-tracking branch exists for the given branch name.
    Returns (remote_name, remote_branch_path, commit_hash) or None.
    
    For example, if branch_name is 'new-feature' and refs/remotes/origin/new-feature exists,
    returns ('origin', 'refs/remotes/origin/new-feature', <commit_hash>).
    """
    remotes_dir = repo.lit_dir / 'refs' / 'remotes'
    if not remotes_dir.exists():
        return None
    
    for remote_dir in remotes_dir.iterdir():
        if remote_dir.is_dir():
            remote_name = remote_dir.name
            branch_file = remote_dir / branch_name
            if branch_file.exists() and branch_file.is_file():
                commit_hash = branch_file.read_text().strip()
                return (remote_name, f"refs/remotes/{remote_name}/{branch_name}", commit_hash)
    
    return None


def create_tracking_branch(repo, branch_name, remote_name, commit_hash):
    """
    Create a local branch that tracks a remote branch.
    
    Args:
        repo: Repository instance
        branch_name: Local branch name to create
        remote_name: Name of the remote (e.g., 'origin')
        commit_hash: Commit hash to point the branch to
    """
    # Create the branch file
    branch_file = repo.lit_dir / 'refs' / 'heads' / branch_name
    branch_file.parent.mkdir(parents=True, exist_ok=True)
    branch_file.write_text(f"{commit_hash}\n")
    
    # TODO: Store tracking info in config (branch.<name>.remote and branch.<name>.merge)
    # For now, just create the branch


@click.command('checkout')
@click.option('-b', '--create-branch', 'create', is_flag=True, help='Create a new branch')
@click.option('--detach', is_flag=True, help='Detach HEAD at named commit')
@click.option('-t', '--track', is_flag=True, help='Set up tracking for the branch')
@click.argument('target')
@click.argument('start_point', required=False, default=None)
def checkout_cmd(create, detach, track, target, start_point):
    """
    Switch branches or restore working tree files.
    
    Switch to a different branch, updating the working directory
    and index to match the branch's HEAD commit.
    Can also checkout a specific commit (creates detached HEAD).
    
    Examples:
        lit checkout main                      # Switch to 'main' branch
        lit checkout feature                   # Switch to 'feature' branch
        lit checkout -b new-feature            # Create and switch to 'new-feature'
        lit checkout -b feature origin/feature # Create 'feature' tracking origin/feature
        lit checkout abc123                    # Checkout commit (detached HEAD)
        lit checkout --detach main             # Detach HEAD at main's commit
        lit checkout new-feature               # Auto-create if origin/new-feature exists
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    try:
        refs_mgr = repo.refs
        
        # Handle -b with start_point (e.g., lit checkout -b feature origin/feature)
        if create and start_point:
            # Resolve start_point to a commit
            commit_hash = refs_mgr.resolve_reference(start_point)
            if not commit_hash:
                click.echo(error(f"Reference not found: {start_point}"))
                raise click.Abort()
            
            # Check if start_point is a remote ref for tracking info
            remote_name = None
            if '/' in start_point:
                parts = start_point.split('/', 1)
                remote_path = repo.lit_dir / 'refs' / 'remotes' / parts[0] / parts[1]
                if remote_path.exists():
                    remote_name = parts[0]
            
            # Create the tracking branch
            create_tracking_branch(repo, target, remote_name, commit_hash)
            
            # Read commit and checkout tree
            commit = repo.read_object(commit_hash)
            if not isinstance(commit, Commit):
                click.echo(error(f"Not a valid commit: {start_point}"))
                raise click.Abort()
            
            file_count = checkout_tree(repo, commit.tree)
            
            # Update HEAD to point to the new branch
            head_file = repo.head_file
            head_file.write_text(f"ref: refs/heads/{target}\n")
            
            if remote_name:
                click.echo(success(f"Switched to new branch '{target}' tracking '{start_point}'"))
            else:
                click.echo(success(f"Switched to new branch '{target}'"))
            click.echo(info(f"Updated {file_count} file(s)"))
            return
        
        # Check if target is a local branch
        is_local_branch = branch_exists(repo, target) and not detach
        
        if is_local_branch or (create and not start_point):
            # Branch checkout (existing or create new from HEAD)
            file_count = checkout_branch(repo, target, create=create)
            
            if create:
                click.echo(success(f"Switched to new branch '{target}'"))
            else:
                click.echo(success(f"Switched to branch '{target}'"))
            
            click.echo(info(f"Updated {file_count} file(s)"))
        else:
            # Target is not a local branch
            # Check if it matches a remote-tracking branch (auto-tracking)
            remote_info = find_remote_tracking_branch(repo, target)
            
            if remote_info and not detach:
                # Auto-create a local tracking branch
                remote_name, remote_ref, commit_hash = remote_info
                
                # Create the local branch
                create_tracking_branch(repo, target, remote_name, commit_hash)
                
                # Read commit and checkout tree
                commit = repo.read_object(commit_hash)
                if not isinstance(commit, Commit):
                    click.echo(error(f"Invalid commit in remote ref"))
                    raise click.Abort()
                
                file_count = checkout_tree(repo, commit.tree)
                
                # Update HEAD to point to the new branch
                head_file = repo.head_file
                head_file.write_text(f"ref: refs/heads/{target}\n")
                
                click.echo(success(f"Switched to new branch '{target}' tracking '{remote_name}/{target}'"))
                click.echo(info(f"Updated {file_count} file(s)"))
            else:
                # Commit checkout (detached HEAD)
                # Try to resolve as commit hash or remote ref
                commit_hash = refs_mgr.resolve_reference(target)
                
                if not commit_hash:
                    click.echo(error(f"Reference not found: {target}"))
                    raise click.Abort()
                
                # Read commit
                try:
                    commit = repo.read_object(commit_hash)
                    if not isinstance(commit, Commit):
                        click.echo(error(f"Not a valid commit: {target}"))
                        raise click.Abort()
                except:
                    click.echo(error(f"Cannot read commit: {target}"))
                    raise click.Abort()
                
                # Checkout the tree
                file_count = checkout_tree(repo, commit.tree)
                
                # Set HEAD to detached state
                refs_mgr.set_head(commit_hash, symbolic=False)
                
                click.echo(warning(f"HEAD is now at {commit_hash[:7]} (detached HEAD)"))
                click.echo(info(f"Updated {file_count} file(s)"))
            
    except click.Abort:
        raise
    except Exception as e:
        click.echo(error(f"Checkout failed: {e}"))
        raise click.Abort()
