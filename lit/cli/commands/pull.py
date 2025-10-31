"""Pull command - fetch and integrate changes from remote."""

import click
from lit.core.repository import Repository
from lit.cli.output import success, error, info


@click.command('pull')
@click.argument('remote', default='origin')
@click.argument('branch', required=False)
@click.option('--no-ff', is_flag=True, help='Create merge commit even if fast-forward is possible')
def pull_cmd(remote, branch, no_ff):
    """
    Fetch from and integrate with another repository.
    
    Incorporates changes from a remote repository into the current branch.
    This is equivalent to running 'lit fetch' followed by 'lit merge'.
    
    REMOTE: Name of remote to pull from (default: origin)
    BRANCH: Branch to pull (default: current branch)
    
    Examples:
        lit pull
        lit pull origin main
        lit pull origin feature-branch
        lit pull --no-ff
    
    Workflow:
        1. Fetch updates from remote
        2. Merge remote branch into current branch
        3. Update working directory
    
    Future enhancements:
        - Rebase mode (--rebase)
        - Fast-forward only mode (--ff-only)
        - Automatic conflict resolution strategies
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    # Check if we're on a branch
    head_content = repo.head_file.read_text().strip()
    if not head_content.startswith('ref: refs/heads/'):
        click.echo(error("Cannot pull in detached HEAD state"))
        raise click.Abort()
    
    current_branch = head_content[16:]
    target_branch = branch or current_branch
    
    try:
        # Step 1: Fetch from remote
        click.echo(info(f"Fetching from '{remote}'..."))
        repo.remote.fetch(remote, target_branch)
        click.echo(success(f"Fetched updates from '{remote}'"))
        
        # Step 2: Merge remote branch
        remote_ref_path = repo.remotes_dir / remote / target_branch
        if not remote_ref_path.exists():
            click.echo(error(f"Remote branch '{remote}/{target_branch}' not found"))
            raise click.Abort()
        
        remote_commit_hash = remote_ref_path.read_text().strip()
        
        # Get current commit
        current_ref_path = repo.heads_dir / current_branch
        if not current_ref_path.exists():
            # No local commits yet, just fast-forward
            current_ref_path.write_text(remote_commit_hash)
            
            # Checkout the commit
            from lit.core.objects import Commit
            commit = repo.read_object(remote_commit_hash)
            if isinstance(commit, Commit):
                repo.remote._checkout_commit(repo, commit)
            
            click.echo(success(f"Fast-forwarded to {remote_commit_hash[:7]}"))
            return
        
        current_commit_hash = current_ref_path.read_text().strip()
        
        # Check if already up to date
        if current_commit_hash == remote_commit_hash:
            click.echo(info("Already up to date."))
            return
        
        # Perform merge
        click.echo(info(f"Merging '{remote}/{target_branch}' into '{current_branch}'..."))
        
        # Check for fast-forward
        can_ff = repo.merge.can_fast_forward(current_commit_hash, remote_commit_hash)
        
        if can_ff and not no_ff:
            # Fast-forward merge
            repo.merge.fast_forward(remote_commit_hash)
            
            # Checkout the new commit
            from lit.core.objects import Commit
            commit = repo.read_object(remote_commit_hash)
            if isinstance(commit, Commit):
                repo.remote._checkout_commit(repo, commit)
            
            click.echo(success(f"Fast-forwarded to {remote_commit_hash[:7]}"))
        else:
            # Three-way merge - need to find common ancestor
            merge_base = repo.merge.find_merge_base(current_commit_hash, remote_commit_hash)
            if not merge_base:
                click.echo(error("No common ancestor found"))
                raise click.Abort()
            
            merge_result = repo.merge.three_way_merge(
                merge_base,
                current_commit_hash,
                remote_commit_hash
            )
            
            if not merge_result.success:
                click.echo(error(f"Merge conflicts detected in {len(merge_result.conflicts)} file(s):"))
                for file in merge_result.conflicts:
                    click.echo(f"  - {file}")
                click.echo(info("⚠️ Conflict resolution is not yet implemented"))
                click.echo(info("Merge has been aborted"))
                repo.merge.abort_merge()
            else:
                # Create merge commit
                from lit.core.objects import Commit
                import time
                
                current_commit = repo.read_object(current_commit_hash)
                remote_commit = repo.read_object(remote_commit_hash)
                
                merge_commit = Commit(
                    tree=merge_result.merged_tree_hash,
                    parents=[current_commit_hash, remote_commit_hash],
                    message=f"Merge branch '{remote}/{target_branch}'",
                    author=current_commit.author,
                    committer=current_commit.author,
                    author_time=int(time.time()),
                    committer_time=int(time.time())
                )
                
                merge_commit_hash = repo.write_object(merge_commit)
                
                # Update branch ref
                repo.refs.write_ref(f"refs/heads/{current_branch}", merge_commit_hash)
                
                # Checkout merged tree
                repo.remote._checkout_commit(repo, merge_commit)
                
                click.echo(success(f"Merged '{remote}/{target_branch}' into '{current_branch}'"))
                click.echo(info(f"Merge commit: {merge_commit_hash[:7]}"))
        
    except Exception as e:
        click.echo(error(f"Pull failed: {str(e)}"))
        raise click.Abort()
