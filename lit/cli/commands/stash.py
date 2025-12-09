"""Stash command for Lit VCS."""

import click
from datetime import datetime
from colorama import Fore, Style

from lit.core.repository import Repository
from lit.operations.stash import StashManager
from lit.cli.output import error, success, info, warning


def parse_stash_ref(ref: str) -> int:
    """
    Parse stash reference to index.
    
    Accepts:
        - "stash@{0}", "stash@{1}", etc.
        - "0", "1", etc.
        
    Returns:
        int: Stash index
        
    Raises:
        ValueError: If invalid format
    """
    if ref.startswith('stash@{') and ref.endswith('}'):
        try:
            return int(ref[7:-1])
        except ValueError:
            raise ValueError(f"Invalid stash reference: {ref}")
    
    try:
        return int(ref)
    except ValueError:
        raise ValueError(f"Invalid stash reference: {ref}")


@click.group('stash', invoke_without_command=True)
@click.pass_context
def stash_cmd(ctx):
    """Stash changes in working directory.
    
    Use 'lit stash' to save changes and clean working directory.
    Use 'lit stash pop' to restore most recent stash.
    Use 'lit stash list' to see all stashes.
    """
    # If no subcommand, default to 'push' (save)
    if ctx.invoked_subcommand is None:
        ctx.invoke(push)


@stash_cmd.command('push')
@click.option('-m', '--message', help='Stash message')
@click.option('-k', '--keep-index', is_flag=True, help='Keep staged changes in index')
def push(message, keep_index):
    """Save changes to stash (default action)."""
    try:
        repo = Repository.find_repository()
        stash = StashManager(repo)
        
        entry = stash.save(message=message, keep_index=keep_index)
        
        if entry:
            click.echo(success(f"Saved working directory and index state"))
            click.echo(info(f"  {entry.message}"))
        else:
            click.echo(info("No local changes to save"))
            
    except FileNotFoundError:
        click.echo(error("Not a lit repository"))
    except Exception as e:
        click.echo(error(f"Failed to stash changes: {e}"))


@stash_cmd.command('list')
def list_stashes():
    """List all stashed changes."""
    try:
        repo = Repository.find_repository()
        stash = StashManager(repo)
        
        entries = stash.list()
        
        if not entries:
            click.echo(info("No stashed changes"))
            return
        
        for i, entry in enumerate(entries):
            # Format timestamp
            dt = datetime.fromtimestamp(entry.timestamp)
            date_str = dt.strftime("%b %d %H:%M")
            
            click.echo(f"{Fore.YELLOW}stash@{{{i}}}{Style.RESET_ALL}: On {entry.branch}: {entry.message}")
            
    except FileNotFoundError:
        click.echo(error("Not a lit repository"))
    except Exception as e:
        click.echo(error(f"Failed to list stashes: {e}"))


@stash_cmd.command('show')
@click.argument('stash_ref', default='0')
def show(stash_ref):
    """Show changes in a stash entry."""
    try:
        repo = Repository.find_repository()
        stash = StashManager(repo)
        
        try:
            index = parse_stash_ref(stash_ref)
        except ValueError as e:
            click.echo(error(str(e)))
            return
        
        details = stash.show(index)
        
        if not details:
            click.echo(error(f"stash@{{{index}}} does not exist"))
            return
        
        entry = details['entry']
        click.echo(f"{Fore.YELLOW}stash@{{{index}}}{Style.RESET_ALL}: {entry.message}")
        click.echo(f"  Branch: {entry.branch}")
        click.echo(f"  Commit: {entry.commit[:7]}")
        click.echo()
        
        if details['work_files']:
            click.echo(f"{Fore.CYAN}Working tree changes:{Style.RESET_ALL}")
            for f in sorted(details['work_files']):
                click.echo(f"  {f}")
        
        if details['index_files']:
            click.echo(f"\n{Fore.GREEN}Staged changes:{Style.RESET_ALL}")
            for f in sorted(details['index_files']):
                click.echo(f"  {f}")
            
    except FileNotFoundError:
        click.echo(error("Not a lit repository"))
    except Exception as e:
        click.echo(error(f"Failed to show stash: {e}"))


@stash_cmd.command('pop')
@click.argument('stash_ref', default='0')
def pop(stash_ref):
    """Apply stash and remove it from the list."""
    try:
        repo = Repository.find_repository()
        stash = StashManager(repo)
        
        try:
            index = parse_stash_ref(stash_ref)
        except ValueError as e:
            click.echo(error(str(e)))
            return
        
        entry = stash.pop(index)
        
        if entry:
            click.echo(success(f"Applied stash@{{{index}}} and removed it"))
            click.echo(info(f"  {entry.message}"))
        else:
            click.echo(error(f"stash@{{{index}}} does not exist"))
            
    except FileNotFoundError:
        click.echo(error("Not a lit repository"))
    except Exception as e:
        click.echo(error(f"Failed to pop stash: {e}"))


@stash_cmd.command('apply')
@click.argument('stash_ref', default='0')
def apply(stash_ref):
    """Apply stash without removing it."""
    try:
        repo = Repository.find_repository()
        stash = StashManager(repo)
        
        try:
            index = parse_stash_ref(stash_ref)
        except ValueError as e:
            click.echo(error(str(e)))
            return
        
        entry = stash.apply(index)
        
        if entry:
            click.echo(success(f"Applied stash@{{{index}}}"))
            click.echo(info(f"  {entry.message}"))
        else:
            click.echo(error(f"stash@{{{index}}} does not exist"))
            
    except FileNotFoundError:
        click.echo(error("Not a lit repository"))
    except Exception as e:
        click.echo(error(f"Failed to apply stash: {e}"))


@stash_cmd.command('drop')
@click.argument('stash_ref', default='0')
def drop(stash_ref):
    """Remove a stash entry without applying it."""
    try:
        repo = Repository.find_repository()
        stash = StashManager(repo)
        
        try:
            index = parse_stash_ref(stash_ref)
        except ValueError as e:
            click.echo(error(str(e)))
            return
        
        entry = stash.drop(index)
        
        if entry:
            click.echo(success(f"Dropped stash@{{{index}}}"))
            click.echo(info(f"  {entry.message}"))
        else:
            click.echo(error(f"stash@{{{index}}} does not exist"))
            
    except FileNotFoundError:
        click.echo(error("Not a lit repository"))
    except Exception as e:
        click.echo(error(f"Failed to drop stash: {e}"))


@stash_cmd.command('clear')
@click.confirmation_option(prompt='Are you sure you want to remove all stashes?')
def clear():
    """Remove all stash entries."""
    try:
        repo = Repository.find_repository()
        stash = StashManager(repo)
        
        count = stash.clear()
        
        if count > 0:
            click.echo(success(f"Dropped {count} stash{'es' if count > 1 else ''}"))
        else:
            click.echo(info("No stashes to clear"))
            
    except FileNotFoundError:
        click.echo(error("Not a lit repository"))
    except Exception as e:
        click.echo(error(f"Failed to clear stashes: {e}"))
