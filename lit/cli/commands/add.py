"""Add command - stage files for commit."""

import click
from pathlib import Path
from lit.core.repository import Repository
from lit.core.index import Index
from lit.cli.output import success, error, info


@click.command('add')
@click.argument('paths', nargs=-1, required=True)
def add_cmd(paths):
    """
    Add file contents to the staging area.
    
    Stage files for the next commit. Modified files must be added
    again to stage the new changes.
    
    Examples:
        lit add file.txt
        lit add src/*.py
        lit add .
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    index = Index()
    index_file = repo.index_file
    
    if index_file.exists():
        index.read(str(index_file))
    
    added_files = []
    failed_files = []
    
    for path_pattern in paths:
        path = Path(path_pattern)
        
        if path.is_absolute():
            resolved_path = path
        else:
            resolved_path = Path.cwd() / path
        
        if not resolved_path.exists():
            failed_files.append((path_pattern, "File not found"))
            continue
        
        if resolved_path.is_file():
            try:
                sha1 = index.add_file(repo, str(resolved_path))
                rel_path = resolved_path.relative_to(repo.work_tree)
                added_files.append(str(rel_path))
            except Exception as e:
                failed_files.append((path_pattern, str(e)))
        
        elif resolved_path.is_dir():
            if resolved_path.name.startswith('.'):
                failed_files.append((path_pattern, "Hidden directory"))
                continue
            
            for file_path in resolved_path.rglob('*'):
                if file_path.is_file() and not any(part.startswith('.') for part in file_path.parts):
                    try:
                        sha1 = index.add_file(repo, str(file_path))
                        rel_path = file_path.relative_to(repo.work_tree)
                        added_files.append(str(rel_path))
                    except Exception as e:
                        failed_files.append((str(file_path), str(e)))
    
    if added_files:
        index.write(str(index_file))
        click.echo(success(f"Added {len(added_files)} file(s) to staging area"))
        for file in added_files:
            click.echo(info(f"  {file}"))
    
    if failed_files:
        click.echo()
        click.echo(error(f"Failed to add {len(failed_files)} file(s):"))
        for file, reason in failed_files:
            click.echo(error(f"  {file}: {reason}"))
    
    if not added_files and not failed_files:
        click.echo(error("No files matched"))
