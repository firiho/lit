"""Merge command for Lit VCS."""

import click
from pathlib import Path
from lit.core.repository import Repository
from lit.cli.output import success, error, warning, info


# Valid auto-resolve strategies
AUTO_STRATEGIES = ['recent', 'ours', 'theirs', 'union']


@click.command('merge')
@click.argument('branch', required=False)
@click.option('--no-ff', is_flag=True, help='Create a merge commit even if fast-forward is possible')
@click.option('--abort', is_flag=True, help='Abort the current merge operation')
@click.option('--auto', 'auto_strategy', is_flag=False, flag_value='recent', default=None,
              help='Auto-resolve conflicts. Strategies: recent (default), ours, theirs, union')
def merge_cmd(branch, no_ff, abort, auto_strategy):
    """
    Merge a branch into the current branch.
    
    BRANCH is the name of the branch to merge into the current branch.
    
    Examples:
        lit merge feature           # Merge feature branch into current branch
        lit merge feature --no-ff   # Force merge commit (no fast-forward)
        lit merge feature --auto    # Auto-resolve conflicts (uses 'recent' strategy)
        lit merge feature --auto=ours    # Auto-resolve: always take our version
        lit merge feature --auto=theirs  # Auto-resolve: always take their version
        lit merge feature --auto=union   # Auto-resolve: include both versions
        lit merge --abort           # Abort current merge (if conflicts exist)
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
    
    # Branch is required for actual merge (not for --abort)
    if not branch:
        click.echo(error("Missing branch name"))
        click.echo(info("Usage: lit merge <branch>"))
        click.echo(info("       lit merge --abort"))
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
    
    # Validate and process auto strategy
    if auto_strategy:
        if auto_strategy not in AUTO_STRATEGIES:
            click.echo(error(f"Invalid auto strategy: {auto_strategy}"))
            click.echo(info(f"Valid strategies: {', '.join(AUTO_STRATEGIES)}"))
            return
        click.echo(info(f"Auto-resolving conflicts with '{auto_strategy}' strategy"))
    
    # Perform merge
    result = repo.merge.merge(branch, allow_fast_forward=not no_ff, auto_strategy=auto_strategy)
    
    if not result.success:
        click.echo(error(f"Merge failed: {result.message}"))
        
        if result.conflicts:
            # Get the target commit hash for saving merge state
            target_hash = repo.refs.read_ref(f"refs/heads/{branch}")
            if not target_hash and '/' in branch:
                target_hash = repo.refs.read_ref(f"refs/remotes/{branch}")
            
            click.echo(error(f"\nConflicts detected in {len(result.conflicts)} file(s):"))
            for conflict in result.conflicts:
                click.echo(error(f"  CONFLICT (content): Merge conflict in {conflict.path}"))
            
            # Write conflict markers to working tree
            repo.merge.write_conflicts_to_working_tree(result.conflicts)
            
            # Save merge state so user can resolve and commit
            repo.merge.save_merge_state(target_hash, result.conflicts)
            
            click.echo(warning("\nAutomatic merge failed; fix conflicts and then commit the result."))
            click.echo(info("\nTo resolve:"))
            click.echo(info("  1. Edit the conflicted files to resolve the conflicts"))
            click.echo(info("  2. Look for conflict markers: <<<<<<< HEAD, =======, >>>>>>>"))
            click.echo(info("  3. Stage the resolved files: lit add <file>"))
            click.echo(info("  4. Complete the merge: lit commit -m \"Merge message\""))
            click.echo(info("\nOr to abort the merge:"))
            click.echo(info("  lit merge --abort"))
        return
    
    if result.is_fast_forward:
        click.echo(success(f"Fast-forward merge to {repo.refs.resolve_head()[:7]}"))
    else:
        if result.merged_tree_hash:
            # Create merge commit
            from lit.core.objects import Commit
            from lit.cli.commands.commit import get_author_info
            
            # Get author info using the same logic as commit command
            # (checks env vars, repo config, then global config)
            author = get_author_info()
            if not author:
                click.echo(error("Could not determine author information"))
                return
            
            # Get target commit for message
            target_hash = repo.refs.read_ref(f"refs/heads/{branch}")
            if not target_hash and '/' in branch:
                target_hash = repo.refs.read_ref(f"refs/remotes/{branch}")
            
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
