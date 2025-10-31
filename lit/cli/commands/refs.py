"""Show-ref command - display references."""

import click
from lit.core.repository import Repository
from lit.cli.output import success, error, info, warning
from colorama import Fore, Style


@click.command('show-ref')
@click.option('--heads', is_flag=True, help='Show only branch references')
@click.option('--tags', is_flag=True, help='Show only tag references')
@click.option('--head', is_flag=True, help='Show HEAD reference')
@click.option('-d', '--dereference', is_flag=True, help='Dereference symbolic references')
def show_ref_cmd(heads, tags, head, dereference):
    """
    Display references in the repository.
    
    Shows all branches, tags, and HEAD with their commit hashes.
    
    Examples:
        lit show-ref              # Show all references
        lit show-ref --heads      # Show only branches
        lit show-ref --tags       # Show only tags
        lit show-ref --head       # Show HEAD information
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    refs_mgr = repo.refs
    shown_any = False
    
    # Show HEAD
    if head or (not heads and not tags):
        head_info = refs_mgr.get_ref_info('HEAD')
        if head_info['exists']:
            shown_any = True
            if head_info['symbolic']:
                click.echo(f"{head_info['target']} {Fore.CYAN}HEAD{Style.RESET_ALL} -> {head_info['symbolic_target']}")
            else:
                # Detached HEAD
                click.echo(f"{head_info['target']} {Fore.YELLOW}HEAD (detached){Style.RESET_ALL}")
    
    # Show branches
    if heads or (not heads and not tags and not head):
        branches = refs_mgr.list_branches()
        if branches:
            shown_any = True
            for branch_name, commit_hash in branches:
                ref_name = f"refs/heads/{branch_name}"
                click.echo(f"{commit_hash} {Fore.GREEN}{ref_name}{Style.RESET_ALL}")
    
    # Show tags
    if tags or (not heads and not tags and not head):
        tag_list = refs_mgr.list_tags()
        if tag_list:
            shown_any = True
            for tag_name, commit_hash in tag_list:
                ref_name = f"refs/tags/{tag_name}"
                click.echo(f"{commit_hash} {Fore.YELLOW}{ref_name}{Style.RESET_ALL}")
    
    if not shown_any:
        click.echo(warning("No references found"))


@click.command('symbolic-ref')
@click.argument('name', required=False)
@click.argument('ref', required=False)
def symbolic_ref_cmd(name, ref):
    """
    Read or set symbolic references.
    
    Examples:
        lit symbolic-ref HEAD              # Show what HEAD points to
        lit symbolic-ref HEAD refs/heads/main  # Set HEAD to point to main
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    refs_mgr = repo.refs
    
    if not name:
        click.echo(error("Reference name required"))
        raise click.Abort()
    
    if ref:
        # Set symbolic reference
        if name == 'HEAD':
            if refs_mgr.set_head(ref if ref.startswith('refs/') else f'refs/heads/{ref}', symbolic=True):
                click.echo(success(f"Set {name} to {ref}"))
            else:
                click.echo(error(f"Failed to set {name}"))
                raise click.Abort()
        else:
            click.echo(error("Only HEAD can be set as symbolic reference"))
            raise click.Abort()
    else:
        # Read symbolic reference
        if name == 'HEAD':
            info = refs_mgr.get_ref_info('HEAD')
            if info['exists'] and info['symbolic']:
                click.echo(info['symbolic_target'])
            elif info['exists']:
                click.echo(error("HEAD is not a symbolic reference (detached HEAD)"))
                raise click.Abort()
            else:
                click.echo(error("HEAD does not exist"))
                raise click.Abort()
        else:
            click.echo(error("Only HEAD supported for now"))
            raise click.Abort()
