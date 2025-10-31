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


@click.command('checkout')
@click.option('-b', '--create-branch', 'create', is_flag=True, help='Create a new branch')
@click.option('--detach', is_flag=True, help='Detach HEAD at named commit')
@click.argument('target')
def checkout_cmd(create, detach, target):
    """
    Switch branches or restore working tree files.
    
    Switch to a different branch, updating the working directory
    and index to match the branch's HEAD commit.
    Can also checkout a specific commit (creates detached HEAD).
    
    Examples:
        lit checkout main             # Switch to 'main' branch
        lit checkout feature          # Switch to 'feature' branch
        lit checkout -b new-feature   # Create and switch to 'new-feature'
        lit checkout abc123           # Checkout commit (detached HEAD)
        lit checkout --detach main    # Detach HEAD at main's commit
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    try:
        # Check if target is a branch or commit
        is_branch = branch_exists(repo, target) and not detach
        
        if is_branch or create:
            # Branch checkout
            file_count = checkout_branch(repo, target, create=create)
            
            if create:
                click.echo(success(f"Switched to new branch '{target}'"))
            else:
                click.echo(success(f"Switched to branch '{target}'"))
            
            click.echo(info(f"Updated {file_count} file(s)"))
        else:
            # Commit checkout (detached HEAD)
            # Try to resolve as commit hash
            refs_mgr = repo.refs
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
