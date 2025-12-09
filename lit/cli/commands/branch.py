"""Branch command - manage branches."""

import click
import re
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


def resolve_ref(repo, ref_str):
    """
    Resolve a reference to a commit hash.
    
    Supports:
    - Branch names (main, feature)
    - Commit hash prefixes (abc123)
    - HEAD~N syntax (HEAD~1, HEAD~2)
    - branch~N syntax (main~1, feature~2)
    
    Returns commit hash or None if not found.
    """
    if not ref_str:
        return None
    
    # Check for ~N suffix (HEAD~1, main~2, etc.)
    tilde_match = re.match(r'^(.+)~(\d+)$', ref_str)
    if tilde_match:
        base_ref = tilde_match.group(1)
        n = int(tilde_match.group(2))
        
        # Resolve the base reference first
        if base_ref.upper() == 'HEAD':
            base_hash = repo.refs.resolve_head()
        else:
            # Try as branch name
            branch_file = repo.lit_dir / 'refs' / 'heads' / base_ref
            if branch_file.exists():
                base_hash = branch_file.read_text().strip()
            else:
                # Try as commit hash
                base_hash = find_commit_by_prefix(repo, base_ref)
        
        if not base_hash:
            return None
        
        # Walk back N commits
        current_hash = base_hash
        for _ in range(n):
            commit = repo.read_object(current_hash)
            if not isinstance(commit, Commit) or not commit.parents:
                return None
            current_hash = commit.parents[0]
        
        return current_hash
    
    # Try as HEAD
    if ref_str.upper() == 'HEAD':
        return repo.refs.resolve_head()
    
    # Try as branch name
    branch_file = repo.lit_dir / 'refs' / 'heads' / ref_str
    if branch_file.exists():
        return branch_file.read_text().strip()
    
    # Try as commit hash prefix
    return find_commit_by_prefix(repo, ref_str)


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
        # Try to resolve reference (supports HEAD~N, branch~N, commit hashes)
        commit_hash = resolve_ref(repo, start_point)
        if not commit_hash:
            click.echo(error(f"Not a valid commit or reference: {start_point}"))
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


def get_remote_branches(repo):
    """Get list of all remote-tracking branches with their commit hashes."""
    remotes_dir = repo.lit_dir / 'refs' / 'remotes'
    
    if not remotes_dir.exists():
        return []
    
    branches = []
    for remote_dir in remotes_dir.iterdir():
        if remote_dir.is_dir():
            remote_name = remote_dir.name
            for branch_file in remote_dir.iterdir():
                if branch_file.is_file():
                    branch_name = branch_file.name
                    commit_hash = branch_file.read_text().strip()
                    full_name = f"{remote_name}/{branch_name}"
                    branches.append((full_name, commit_hash))
    
    return sorted(branches, key=lambda x: x[0])


@click.command('branch')
@click.option('-d', '--delete', 'delete_branch_name', metavar='BRANCH', help='Delete a branch')
@click.option('-D', '--force-delete', 'force_delete_name', metavar='BRANCH', help='Force delete a branch')
@click.option('-v', '--verbose', is_flag=True, help='Show commit hash and message')
@click.option('-a', '--all', 'show_all', is_flag=True, help='List all branches (including remote)')
@click.option('-r', '--remotes', is_flag=True, help='List only remote-tracking branches')
@click.argument('branch_name', required=False)
@click.argument('start_point', required=False)
def branch_cmd(delete_branch_name, force_delete_name, verbose, show_all, remotes, branch_name, start_point):
    """
    List, create, or delete branches.
    
    With no arguments, lists all local branches. Current branch is highlighted with *.
    With one argument, creates a new branch at HEAD.
    With two arguments, creates a new branch at the specified commit.
    
    Examples:
        lit branch                    # List local branches
        lit branch -r                 # List remote-tracking branches
        lit branch -a                 # List all branches (local and remote)
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
    current_branch = get_current_branch(repo)
    
    # List local branches (unless -r flag)
    if not remotes:
        branches = get_all_branches(repo)
        
        if not branches and not show_all and not remotes:
            click.echo(warning("No branches found"))
            return
        
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
    
    # List remote branches (if -r or -a flag)
    if remotes or show_all:
        remote_branches = get_remote_branches(repo)
        
        if not remote_branches and remotes:
            click.echo(warning("No remote-tracking branches found"))
            click.echo(info("Use 'lit fetch' to update remote-tracking branches"))
            return
        
        for branch_name, commit_hash in remote_branches:
            prefix = "  "
            name_color = Fore.RED
            
            if verbose:
                commit_msg = get_commit_info(repo, commit_hash)
                click.echo(f"{prefix}{name_color}{branch_name:<20}{Style.RESET_ALL} {commit_hash[:7]} {commit_msg}")
            else:
                click.echo(f"{prefix}{name_color}{branch_name}{Style.RESET_ALL}")
