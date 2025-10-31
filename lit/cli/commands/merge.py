"""Merge command for Lit VCS."""

import click
from pathlib import Path
from lit.core.repository import Repository
from lit.cli.output import success, error, warning, info


@click.command('merge')
@click.argument('branch')
@click.option('--no-ff', is_flag=True, help='Create a merge commit even if fast-forward is possible')
@click.option('--abort', is_flag=True, help='Abort the current merge operation')
def merge_cmd(branch, no_ff, abort):
    """
    Merge a branch into the current branch.
    
    BRANCH is the name of the branch to merge into the current branch.
    
    Examples:
        lit merge feature       # Merge feature branch into current branch
        lit merge feature --no-ff  # Force merge commit (no fast-forward)
        lit merge --abort       # Abort current merge (if conflicts exist)
    """
    # Find repository
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        return
    
    if abort:
        # Abort ongoing merge
        if not repo.merge.is_merge_in_progress():
            click.echo(error("No merge in progress"))
            return
        
        if repo.merge.abort_merge():
            click.echo(success("Merge aborted"))
            click.echo(info("Working tree has been reset"))
        else:
            click.echo(error("Failed to abort merge"))
        return
    
    # Check if merge is already in progress
    if repo.merge.is_merge_in_progress():
        click.echo(error("Merge already in progress"))
        click.echo(info("Resolve conflicts and commit, or run 'lit merge --abort'"))
        return
    
    # Check if we're in a clean state
    current_branch = repo.refs.get_current_branch()
    if not current_branch:
        click.echo(error("Cannot merge in detached HEAD state"))
        return
    
    # Get current commit
    current_hash = repo.refs.resolve_head()
    if not current_hash:
        click.echo(error("No commits on current branch"))
        return
    
    click.echo(info(f"Merging branch '{branch}' into '{current_branch}'..."))
    
    # Perform merge
    result = repo.merge.merge(branch, allow_fast_forward=not no_ff)
    
    if not result.success:
        click.echo(error(f"Merge failed: {result.message}"))
        
        if result.conflicts:
            click.echo(error(f"\nConflicts detected in {len(result.conflicts)} file(s):"))
            for conflict in result.conflicts:
                click.echo(error(f"  - {conflict.path}"))
            
            # Write conflict markers to working tree
            click.echo(info("\nWriting conflict markers to files..."))
            repo.merge.write_conflicts_to_working_tree(result.conflicts)
            
            click.echo(warning("\n⚠️  Conflict resolution is not yet implemented"))
            click.echo(info("Files with conflicts have been marked with conflict markers:"))
            click.echo(info("  <<<<<<< HEAD"))
            click.echo(info("  (your changes)"))
            click.echo(info("  ======="))
            click.echo(info("  (their changes)"))
            click.echo(info("  >>>>>>> branch"))
            click.echo(info("\nAutomatically aborting merge..."))
            
            # Auto-abort on conflicts (conflict resolution upcoming feature)
            repo.merge.clear_merge_state()
            click.echo(success("Merge aborted due to conflicts"))
        return
    
    if result.is_fast_forward:
        click.echo(success(f"Fast-forward merge to {repo.refs.resolve_head()[:7]}"))
    else:
        if result.merged_tree_hash:
            # Create merge commit
            from lit.core.objects import Commit
            
            # Get config for author/committer
            import configparser
            config = configparser.ConfigParser()
            config_file = repo.config_file
            
            if config_file.exists():
                config.read(str(config_file))
            
            if 'user' not in config or 'name' not in config['user'] or 'email' not in config['user']:
                click.echo(error("Please configure user.name and user.email first:"))
                click.echo(info("  lit config user.name 'Your Name'"))
                click.echo(info("  lit config user.email 'your.email@example.com'"))
                return
            
            user_name = config['user']['name']
            user_email = config['user']['email']
            author = f"{user_name} <{user_email}>"
            
            # Get target commit for message
            target_hash = repo.refs.read_ref(f"refs/heads/{branch}")
            
            # Create merge commit
            commit = Commit.create(
                tree_hash=result.merged_tree_hash,
                parent_hashes=[current_hash, target_hash],
                author=author,
                committer=author,
                message=f"Merge branch '{branch}' into {current_branch}"
            )
            
            # Write commit and update HEAD
            commit_hash = repo.write_object(commit)
            repo.refs.write_ref(f"refs/heads/{current_branch}", commit_hash)
            
            # Update working tree to merged state
            repo.remote._checkout_commit(repo, commit)
            
            click.echo(success(f"Merge commit created: {commit_hash[:7]}"))
            click.echo(success(f"Merged '{branch}' into '{current_branch}'"))
        else:
            click.echo(success(result.message))
