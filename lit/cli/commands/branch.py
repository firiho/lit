"""Branch command - manage branches."""

import click
from pathlib import Path
from lit.core.repository import Repository
from lit.core.objects import Commit
from lit.cli.output import success, error, info, warning
from colorama import Fore, Style


def get_current_branch(repo):
    """Get the name of the current branch."""
    head_file = repo.head_file
    
    if not head_file.exists():
        return None
    
    head_content = head_file.read_text().strip()
    
    if head_content.startswith('ref: refs/heads/'):
        return head_content[16:]  # Extract branch name
    
    return None  # Detached HEAD


def get_all_branches(repo):
    """Get list of all branches with their commit hashes."""
    refs_dir = repo.lit_dir / 'refs' / 'heads'
    
    if not refs_dir.exists():
        return []
    
    branches = []
    for branch_file in refs_dir.iterdir():
        if branch_file.is_file():
            branch_name = branch_file.name
            commit_hash = branch_file.read_text().strip()
            branches.append((branch_name, commit_hash))
    
    return sorted(branches, key=lambda x: x[0])


def get_commit_info(repo, commit_hash):
    """Get commit message summary."""
    try:
        commit = repo.read_object(commit_hash)
        if isinstance(commit, Commit):
            message = commit.message.split('\n')[0]
            if len(message) > 50:
                message = message[:47] + "..."
            return message
    except:
        pass
    return "Invalid commit"


def find_commit_by_prefix(repo, prefix):
    """Find commit by hash prefix."""
    if len(prefix) == 40:
        return prefix
    
    objects_dir = repo.objects_dir
    matches = []
    
    if len(prefix) >= 2:
        subdir = objects_dir / prefix[:2]
        if subdir.exists():
            for obj_file in subdir.iterdir():
                full_hash = prefix[:2] + obj_file.name
                if full_hash.startswith(prefix):
                    matches.append(full_hash)
    else:
        for subdir in objects_dir.iterdir():
            if subdir.is_dir() and len(subdir.name) == 2:
                for obj_file in subdir.iterdir():
                    full_hash = subdir.name + obj_file.name
                    if full_hash.startswith(prefix):
                        matches.append(full_hash)
    
    if len(matches) == 1:
        return matches[0]
    return None


def branch_exists(repo, branch_name):
    """Check if a branch exists."""
    branch_file = repo.lit_dir / 'refs' / 'heads' / branch_name
    return branch_file.exists()


def create_branch(repo, branch_name, start_point=None):
    """Create a new branch."""
    # Check if branch already exists
    if branch_exists(repo, branch_name):
        click.echo(error(f"Branch '{branch_name}' already exists"))
        raise click.Abort()
    
    # Determine starting commit
    if start_point:
        # Try to resolve commit hash
        commit_hash = find_commit_by_prefix(repo, start_point)
        if not commit_hash:
            click.echo(error(f"Not a valid commit: {start_point}"))
            raise click.Abort()
    else:
        # Use current HEAD
        head_file = repo.head_file
        if not head_file.exists():
            click.echo(error("No commits yet - cannot create branch"))
            raise click.Abort()
        
        head_content = head_file.read_text().strip()
        if head_content.startswith('ref: '):
            ref_path = head_content[5:]
            ref_file = repo.lit_dir / ref_path
            if not ref_file.exists():
                click.echo(error("Current branch has no commits"))
                raise click.Abort()
            commit_hash = ref_file.read_text().strip()
        else:
            commit_hash = head_content
    
    # Validate commit
    try:
        commit = repo.read_object(commit_hash)
        if not isinstance(commit, Commit):
            click.echo(error(f"Not a valid commit: {commit_hash}"))
            raise click.Abort()
    except:
        click.echo(error(f"Commit not found: {commit_hash}"))
        raise click.Abort()
    
    # Create branch reference
    branch_file = repo.lit_dir / 'refs' / 'heads' / branch_name
    branch_file.parent.mkdir(parents=True, exist_ok=True)
    branch_file.write_text(commit_hash + '\n')
    
    return commit_hash


def delete_branch(repo, branch_name, force=False):
    """Delete a branch."""
    # Check if branch exists
    if not branch_exists(repo, branch_name):
        click.echo(error(f"Branch '{branch_name}' not found"))
        raise click.Abort()
    
    # Check if it's the current branch
    current_branch = get_current_branch(repo)
    if current_branch == branch_name:
        click.echo(error(f"Cannot delete the current branch '{branch_name}'"))
        raise click.Abort()
    
    # TODO: Check if branch is merged (unless force=True)
    # For now, we'll just delete it
    
    branch_file = repo.lit_dir / 'refs' / 'heads' / branch_name
    branch_file.unlink()


@click.command('branch')
@click.option('-d', '--delete', 'delete_branch_name', metavar='BRANCH', help='Delete a branch')
@click.option('-D', '--force-delete', 'force_delete_name', metavar='BRANCH', help='Force delete a branch')
@click.option('-v', '--verbose', is_flag=True, help='Show commit hash and message')
@click.option('-a', '--all', is_flag=True, help='List all branches (including remote)')
@click.argument('branch_name', required=False)
@click.argument('start_point', required=False)
def branch_cmd(delete_branch_name, force_delete_name, verbose, all, branch_name, start_point):
    """
    List, create, or delete branches.
    
    With no arguments, lists all branches. Current branch is highlighted with *.
    With one argument, creates a new branch at HEAD.
    With two arguments, creates a new branch at the specified commit.
    
    Examples:
        lit branch                    # List all branches
        lit branch feature            # Create 'feature' branch at HEAD
        lit branch hotfix abc123      # Create 'hotfix' branch at commit abc123
        lit branch -d feature         # Delete 'feature' branch
        lit branch -v                 # List branches with commit info
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    # Handle delete operations
    if delete_branch_name:
        delete_branch(repo, delete_branch_name, force=False)
        click.echo(success(f"Deleted branch {delete_branch_name}"))
        return
    
    if force_delete_name:
        delete_branch(repo, force_delete_name, force=True)
        click.echo(success(f"Deleted branch {force_delete_name}"))
        return
    
    # Handle branch creation
    if branch_name:
        commit_hash = create_branch(repo, branch_name, start_point)
        click.echo(success(f"Created branch '{branch_name}' at {commit_hash[:7]}"))
        return
    
    # List branches
    branches = get_all_branches(repo)
    
    if not branches:
        click.echo(warning("No branches found"))
        return
    
    current_branch = get_current_branch(repo)
    
    for branch_name, commit_hash in branches:
        is_current = branch_name == current_branch
        
        if is_current:
            prefix = f"{Fore.GREEN}* {Style.RESET_ALL}"
            name_color = Fore.GREEN
        else:
            prefix = "  "
            name_color = ""
        
        if verbose:
            commit_msg = get_commit_info(repo, commit_hash)
            click.echo(f"{prefix}{name_color}{branch_name:<20}{Style.RESET_ALL} {commit_hash[:7]} {commit_msg}")
        else:
            click.echo(f"{prefix}{name_color}{branch_name}{Style.RESET_ALL}")
