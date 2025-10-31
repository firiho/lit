"""Switch command - modern alternative to checkout for switching branches."""

import click
from lit.core.repository import Repository
from lit.cli.output import success, error, info
from lit.cli.commands.checkout import checkout_branch


@click.command('switch')
@click.option('-c', '--create', is_flag=True, help='Create a new branch')
@click.argument('branch_name')
def switch_cmd(create, branch_name):
    """
    Switch to a branch (modern alternative to checkout).
    
    This is a more intuitive alternative to 'lit checkout' that only
    handles branch switching (not file restoration).
    
    Examples:
        lit switch main          # Switch to 'main' branch
        lit switch feature       # Switch to 'feature' branch  
        lit switch -c hotfix     # Create and switch to 'hotfix' branch
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    try:
        file_count = checkout_branch(repo, branch_name, create=create)
        
        if create:
            click.echo(success(f"Switched to a new branch '{branch_name}'"))
        else:
            click.echo(success(f"Switched to branch '{branch_name}'"))
        
        click.echo(info(f"Updated {file_count} file(s)"))
        
    except click.Abort:
        raise
    except Exception as e:
        click.echo(error(f"Switch failed: {e}"))
        raise click.Abort()
