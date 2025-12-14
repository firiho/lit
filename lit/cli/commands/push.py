"""Push command - update remote refs with local commits."""

import click
from lit.core.repository import Repository
from lit.cli.output import success, error, info


@click.command('push')
@click.argument('remote', default='origin')
@click.argument('branch', required=False)
@click.option('--force', '-f', is_flag=True, help='Force push (not recommended)')
@click.option('--all', is_flag=True, help='Push all branches')
def push_cmd(remote, branch, force, all):
    """
    Update remote repository with local commits.
    
    Uploads local commits to a remote repository and updates
    the remote branch to match your local branch.
    
    REMOTE: Name of remote to push to (default: origin)
    BRANCH: Branch to push (default: current branch)
    
    Examples:
        lit push
        lit push origin main
        lit push origin feature-branch
        lit push --all
    
    Safety:
        - Prevents non-fast-forward updates by default
        - Use --force to override (not recommended)
    
    Future enhancements:
        - Push tags (--tags)
        - Delete remote branches (--delete)
        - Push to multiple remotes
        - Pre-push hooks
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    # Check if remote exists
    url = repo.remote.get_remote_url(remote)
    if not url:
        click.echo(error(f"Remote '{remote}' not found"))
        click.echo(info("Use 'lit remote add' to add a remote"))
        raise click.Abort()
    
    if all:
        # Push all branches
        branches = [b.name for b in repo.heads_dir.iterdir() if b.is_file()]
        if not branches:
            click.echo(info("No branches to push"))
            return
        
        for branch_name in branches:
            try:
                click.echo(info(f"Pushing branch '{branch_name}'..."))
                repo.remote.push(remote, branch_name)
                click.echo(success(f"Pushed '{branch_name}' to '{remote}'"))
            except Exception as e:
                click.echo(error(f"Failed to push '{branch_name}': {str(e)}"))
        return
    
    # Determine branch to push
    if not branch:
        head_content = repo.head_file.read_text().strip()
        if not head_content.startswith('ref: refs/heads/'):
            click.echo(error("Cannot push from detached HEAD state"))
            click.echo(info("Specify a branch: lit push origin <branch>"))
            raise click.Abort()
        branch = head_content[16:]
    
    # Check if branch exists locally
    local_ref = repo.heads_dir / branch
    if not local_ref.exists():
        click.echo(error(f"Branch '{branch}' not found"))
        raise click.Abort()
    
    local_commit = local_ref.read_text().strip()
    
    # Fetch current remote state to check for conflicts
    # (In Lit, this happens automatically during push)
    try:
        repo.remote.fetch(remote, branch)
    except:
        # Remote branch might not exist yet, which is fine
        pass
    
    # Check remote branch state (if it exists)
    remote_ref = repo.remotes_dir / remote / branch
    if remote_ref.exists() and not force:
        remote_commit = remote_ref.read_text().strip()
        
        if remote_commit == local_commit:
            click.echo(info("Everything up-to-date"))
            return
        
        # Check if this would be a fast-forward
        if not repo.merge.can_fast_forward(remote_commit, local_commit):
            click.echo(error("Push rejected: not a fast-forward"))
            click.echo(info("Pull the latest changes first: lit pull"))
            click.echo(info("Or force push (dangerous): lit push --force"))
            raise click.Abort()
    
    try:
        click.echo(info(f"Pushing to '{remote}/{branch}'..."))
        repo.remote.push(remote, branch)
        click.echo(success(f"Pushed '{branch}' to '{remote}'"))
        click.echo(info(f"{local_commit[:7]} -> {branch}"))
        
    except Exception as e:
        click.echo(error(f"Push failed: {str(e)}"))
        raise click.Abort()
