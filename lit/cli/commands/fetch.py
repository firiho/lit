"""Fetch command - download objects and refs from remote repository."""

import click
from lit.core.repository import Repository
from lit.cli.output import success, error, info, warning


@click.command('fetch')
@click.argument('remote', default='origin')
@click.option('--all', 'fetch_all', is_flag=True, help='Fetch from all remotes')
@click.option('-v', '--verbose', is_flag=True, help='Be verbose')
def fetch_cmd(remote, fetch_all, verbose):
    """
    Download objects and refs from a remote repository.
    
    Fetches branches and commits from a remote repository and updates
    remote-tracking branches. Does NOT modify your local branches or
    working directory.
    
    REMOTE is the name of the remote to fetch from (default: origin).
    
    Examples:
        lit fetch              # Fetch from origin
        lit fetch upstream     # Fetch from upstream remote
        lit fetch --all        # Fetch from all configured remotes
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        return
    
    remotes_to_fetch = []
    
    if fetch_all:
        # Fetch from all remotes
        all_remotes = repo.remote.list_remotes()
        if not all_remotes:
            click.echo(error("No remotes configured"))
            click.echo(info("Use 'lit remote add <name> <url>' to add a remote"))
            return
        remotes_to_fetch = list(all_remotes.keys())
    else:
        # Fetch from specified remote
        url = repo.remote.get_remote_url(remote)
        if not url:
            click.echo(error(f"Remote '{remote}' not found"))
            click.echo(info("Use 'lit remote' to list configured remotes"))
            click.echo(info("Use 'lit remote add <name> <url>' to add a remote"))
            return
        remotes_to_fetch = [remote]
    
    for remote_name in remotes_to_fetch:
        url = repo.remote.get_remote_url(remote_name)
        
        if verbose:
            click.echo(info(f"Fetching from {remote_name} ({url})..."))
        else:
            click.echo(info(f"Fetching from {remote_name}..."))
        
        try:
            # Get current remote refs before fetch for comparison
            remote_refs_dir = repo.remotes_dir / remote_name
            old_refs = {}
            if remote_refs_dir.exists():
                for ref_file in remote_refs_dir.iterdir():
                    if ref_file.is_file():
                        old_refs[ref_file.name] = ref_file.read_text().strip()
            
            # Perform fetch
            repo.remote.fetch(remote_name)
            
            # Get new refs after fetch
            new_refs = {}
            if remote_refs_dir.exists():
                for ref_file in remote_refs_dir.iterdir():
                    if ref_file.is_file():
                        new_refs[ref_file.name] = ref_file.read_text().strip()
            
            # Report changes
            updated = 0
            new_branches = 0
            
            for branch, commit in new_refs.items():
                if branch not in old_refs:
                    new_branches += 1
                    if verbose:
                        click.echo(success(f"  * [new branch] {branch} -> {remote_name}/{branch}"))
                elif old_refs[branch] != commit:
                    updated += 1
                    if verbose:
                        old_short = old_refs[branch][:7]
                        new_short = commit[:7]
                        click.echo(success(f"  {old_short}..{new_short} {branch} -> {remote_name}/{branch}"))
            
            if new_branches == 0 and updated == 0:
                click.echo(info(f"  Already up to date."))
            else:
                summary = []
                if new_branches > 0:
                    summary.append(f"{new_branches} new branch(es)")
                if updated > 0:
                    summary.append(f"{updated} updated")
                click.echo(success(f"  Fetched: {', '.join(summary)}"))
                
        except NotImplementedError as e:
            click.echo(error(f"  {e}"))
        except Exception as e:
            click.echo(error(f"  Failed to fetch: {e}"))
    
    click.echo()
    click.echo(success("Fetch complete"))
