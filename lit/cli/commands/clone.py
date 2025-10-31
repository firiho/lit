"""Clone command - clone a repository into a new directory."""

import click
from pathlib import Path
from lit.core.repository import Repository
from lit.cli.output import success, error, info


@click.command('clone')
@click.argument('repository')
@click.argument('directory', required=False)
@click.option('--bare', is_flag=True, help='Create a bare repository')
def clone_cmd(repository, directory, bare):
    """
    Clone a repository into a new directory.
    
    Creates a copy of an existing repository with all its history,
    branches, and tags. Sets up remote tracking automatically.
    
    REPOSITORY: Path or URL to source repository
    DIRECTORY: Destination directory (optional, inferred from repository name)
    
    Options:
        --bare    Create a bare repository (no working directory)
                  Bare repos are typically used as central shared repositories
    
    Examples:
        lit clone /path/to/source my-project
        lit clone --bare /path/to/source origin.git
        lit clone file:///path/to/source
        lit clone ../other-repo
    
    Currently supports:
        - Local file system cloning (file:// or direct paths)
        - Bare repository cloning
        - Automatic remote tracking setup
        - Default branch checkout
    
    Future enhancements:
        - HTTPS/SSH protocols
        - Shallow clones (--depth)
        - Specific branch cloning (--branch)
    """
    
    # Determine destination directory
    if not directory:
        # Infer from repository path
        repo_path = Path(repository)
        if repo_path.name.endswith('.lit'):
            directory = repo_path.name[:-4]
        else:
            directory = repo_path.name
        
        # For bare repos, add .git suffix if not present
        if bare and not directory.endswith('.git'):
            directory = directory + '.git'
        # Remove .git suffix for non-bare if present
        elif not bare and directory.endswith('.git'):
            directory = directory[:-4]
    
    try:
        if bare:
            click.echo(info(f"Cloning into bare repository '{directory}'..."))
        else:
            click.echo(info(f"Cloning into '{directory}'..."))
        
        # Create temporary repository to access RemoteManager
        temp_repo = Repository('.')
        cloned_repo = temp_repo.remote.clone(repository, directory, bare=bare)
        
        # Count objects and refs for reporting
        object_count = sum(1 for _ in cloned_repo.objects_dir.rglob('*') if _.is_file())
        
        if bare:
            click.echo(success(f"Cloned bare repository with {object_count} objects"))
            click.echo(info(f"Bare repository ready for push/pull operations"))
        else:
            # Get current branch
            head_content = cloned_repo.head_file.read_text().strip()
            current_branch = "main"
            if head_content.startswith('ref: refs/heads/'):
                current_branch = head_content[16:]
            
            click.echo(success(f"Cloned repository with {object_count} objects"))
            click.echo(info(f"Checked out branch '{current_branch}'"))
            click.echo(info(f"Remote 'origin' set to '{repository}'"))
        
    except Exception as e:
        click.echo(error(f"Failed to clone repository: {str(e)}"))
        raise click.Abort()
