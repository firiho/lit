"""Remote command - manage remote repositories."""

import click
from lit.core.repository import Repository
from lit.cli.output import success, error, info


@click.group('remote')
def remote_cmd():
    """Manage remote repositories."""
    pass


@remote_cmd.command('add')
@click.argument('name')
@click.argument('url')
def remote_add(name, url):
    """
    Add a remote repository.
    
    NAME: Remote name (e.g., 'origin', 'upstream')
    URL: Remote repository URL or path
    
    Examples:
        lit remote add origin /path/to/repo
        lit remote add origin file:///absolute/path
        lit remote add upstream ../other-repo
    
    Future: Will support https://, ssh://, git@ URLs
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    try:
        # Check if remote already exists
        existing = repo.remote.get_remote_url(name)
        if existing:
            click.echo(error(f"Remote '{name}' already exists: {existing}"))
            click.echo(info(f"Use 'lit remote set-url {name} <url>' to change it"))
            raise click.Abort()
        
        repo.remote.add_remote(name, url)
        click.echo(success(f"Added remote '{name}': {url}"))
        
    except Exception as e:
        click.echo(error(f"Failed to add remote: {str(e)}"))
        raise click.Abort()


@remote_cmd.command('remove')
@click.argument('name')
def remote_remove(name):
    """
    Remove a remote repository.
    
    NAME: Remote name to remove
    
    Example:
        lit remote remove origin
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    try:
        url = repo.remote.get_remote_url(name)
        if not url:
            click.echo(error(f"Remote '{name}' not found"))
            raise click.Abort()
        
        repo.remote.remove_remote(name)
        click.echo(success(f"Removed remote '{name}'"))
        
    except Exception as e:
        click.echo(error(f"Failed to remove remote: {str(e)}"))
        raise click.Abort()


@remote_cmd.command('list')
@click.option('--verbose', '-v', is_flag=True, help='Show URLs')
def remote_list(verbose):
    """
    List remote repositories.
    
    Examples:
        lit remote list
        lit remote list -v
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    remotes = repo.remote.list_remotes()
    
    if not remotes:
        click.echo(info("No remotes configured"))
        return
    
    for name, url in remotes.items():
        if verbose:
            click.echo(f"{name}\t{url}")
        else:
            click.echo(name)


@remote_cmd.command('get-url')
@click.argument('name')
def remote_get_url(name):
    """
    Get URL for a remote.
    
    NAME: Remote name
    
    Example:
        lit remote get-url origin
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    url = repo.remote.get_remote_url(name)
    if not url:
        click.echo(error(f"Remote '{name}' not found"))
        raise click.Abort()
    
    click.echo(url)


@remote_cmd.command('set-url')
@click.argument('name')
@click.argument('url')
def remote_set_url(name, url):
    """
    Change URL for a remote.
    
    NAME: Remote name
    URL: New URL or path
    
    Example:
        lit remote set-url origin /new/path
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    try:
        existing = repo.remote.get_remote_url(name)
        if not existing:
            click.echo(error(f"Remote '{name}' not found"))
            click.echo(info(f"Use 'lit remote add {name} {url}' to add it"))
            raise click.Abort()
        
        # Remove and re-add with new URL
        repo.remote.remove_remote(name)
        repo.remote.add_remote(name, url)
        
        click.echo(success(f"Changed '{name}' URL to: {url}"))
        
    except Exception as e:
        click.echo(error(f"Failed to set URL: {str(e)}"))
        raise click.Abort()
