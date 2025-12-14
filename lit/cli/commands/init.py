"""Initialize a new Lit repository."""

import click
from pathlib import Path
from lit.core.repository import Repository
from lit.cli.output import success, error, info


@click.command('init')
@click.argument('path', default='.')
@click.option('--bare', is_flag=True, help='Create a bare repository')
def init_cmd(path, bare):
    """
    Initialize a new Lit repository.
    
    Creates a .lit directory with the necessary structure for version control.
    Similar to 'lit init'.
    
    Examples:
        lit init                    # Initialize in current directory
        lit init my-project         # Initialize in my-project directory
        lit init --bare repo.lit    # Create a bare repository
    """
    if bare:
        click.echo(error("Bare repositories not yet implemented"))
        raise click.Abort()
    
    try:
        # Resolve the path
        repo_path = Path(path).resolve()
        
        # Check if repository already exists
        if (repo_path / '.lit').exists():
            click.echo(error(f"Repository already exists at {repo_path}"))
            click.echo(info("Use an empty directory or different path"))
            raise click.Abort()
        
        # Create directory if it doesn't exist
        if not repo_path.exists():
            repo_path.mkdir(parents=True)
            click.echo(info(f"Created directory {repo_path}"))
        
        # Initialize repository
        repo = Repository(str(repo_path))
        repo.init()
        
        # Success message
        click.echo()
        click.echo(success(f"Initialized empty Lit repository in {repo.lit_dir}"))
        click.echo()
        click.echo(info("Repository structure created:"))
        click.echo(info(f"  .lit/objects/     - Object database"))
        click.echo(info(f"  .lit/refs/        - Branch and tag references"))
        click.echo(info(f"  .lit/HEAD         - Current branch pointer"))
        click.echo(info(f"  .lit/config       - Repository configuration"))
        click.echo()
        click.echo(info("You can now start tracking files with:"))
        click.echo(info(f"  cd {repo_path.name if repo_path.name != '.' else repo_path}"))
        click.echo(info("  lit add <file>"))
        click.echo(info("  lit commit -m 'message'"))
        
    except PermissionError:
        click.echo(error(f"Permission denied: Cannot create repository at {path}"))
        raise click.Abort()
    except Exception as e:
        click.echo(error(f"Failed to initialize repository: {e}"))
        raise click.Abort()
