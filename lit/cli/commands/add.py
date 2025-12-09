"""Add command - stage files for commit."""

import click
from pathlib import Path
from lit.core.repository import Repository
from lit.core.index import Index
from lit.utils.ignore import get_ignore_matcher
from lit.cli.output import success, error, info, warning


def has_conflict_markers(file_path: Path) -> bool:
    """Check if a file still contains conflict markers."""
    try:
        content = file_path.read_text(errors='replace')
        markers = ['<<<<<<< HEAD', '=======', '>>>>>>>']
        return any(marker in content for marker in markers)
    except:
        return False


@click.command('add')
@click.argument('paths', nargs=-1, required=True)
@click.option('-f', '--force', is_flag=True, help='Add ignored files')
def add_cmd(paths, force):
    """
    Add file contents to the staging area.
    
    Stage files for the next commit. Modified files must be added
    again to stage the new changes.
    
    Files matching patterns in .litignore are skipped unless --force is used.
    
    During a merge with conflicts, adding a file marks it as resolved.
    
    Examples:
        lit add file.txt
        lit add src/*.py
        lit add .
        lit add -f ignored_file.txt
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    # Check if merge is in progress
    merge_in_progress = repo.merge.is_merge_in_progress()
    
    # Load ignore patterns
    ignore_matcher = get_ignore_matcher(repo.work_tree)
    
    index = Index()
    index_file = repo.index_file
    
    if index_file.exists():
        index.read(str(index_file))
    
    added_files = []
    failed_files = []
    resolved_conflicts = []
    conflict_warnings = []
    ignored_files = []
    
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
                rel_path = resolved_path.relative_to(repo.work_tree)
                rel_path_str = str(rel_path).replace('\\', '/')
                
                # Check if file is ignored
                if not force and ignore_matcher.is_ignored(rel_path_str):
                    ignored_files.append(rel_path_str)
                    continue
                
                # Check for conflict markers if merge is in progress
                if merge_in_progress and has_conflict_markers(resolved_path):
                    conflict_warnings.append(rel_path_str)
                
                sha1 = index.add_file(repo, str(resolved_path))
                added_files.append(rel_path_str)
                
                # Track resolved conflicts
                if merge_in_progress:
                    resolved_conflicts.append(rel_path_str)
            except Exception as e:
                failed_files.append((path_pattern, str(e)))
        
        elif resolved_path.is_dir():
            if resolved_path.name.startswith('.'):
                failed_files.append((path_pattern, "Hidden directory"))
                continue
            
            # Check if directory is ignored
            try:
                dir_rel_path = resolved_path.relative_to(repo.work_tree)
                dir_rel_str = str(dir_rel_path).replace('\\', '/')
                if not force and ignore_matcher.is_ignored(dir_rel_str, is_dir=True):
                    ignored_files.append(dir_rel_str + '/')
                    continue
            except ValueError:
                pass  # Directory outside repo
            
            for file_path in resolved_path.rglob('*'):
                if file_path.is_file():
                    try:
                        rel_path = file_path.relative_to(repo.work_tree)
                        rel_path_str = str(rel_path).replace('\\', '/')
                        
                        # Skip hidden files/dirs (but also check ignore patterns)
                        if any(part.startswith('.') for part in rel_path.parts):
                            continue
                        
                        # Check if file is ignored
                        if not force and ignore_matcher.is_ignored(rel_path_str):
                            ignored_files.append(rel_path_str)
                            continue
                        
                        # Check for conflict markers if merge is in progress
                        if merge_in_progress and has_conflict_markers(file_path):
                            conflict_warnings.append(rel_path_str)
                        
                        sha1 = index.add_file(repo, str(file_path))
                        added_files.append(rel_path_str)
                        
                        if merge_in_progress:
                            resolved_conflicts.append(rel_path_str)
                    except Exception as e:
                        failed_files.append((str(file_path), str(e)))
    
    if added_files:
        index.write(str(index_file))
        click.echo(success(f"Added {len(added_files)} file(s) to staging area"))
        for file in added_files:
            click.echo(info(f"  {file}"))
    
    # Show ignored files hint
    if ignored_files:
        click.echo()
        click.echo(warning(f"Ignored {len(ignored_files)} file(s) matching .litignore patterns"))
        if len(ignored_files) <= 5:
            for file in ignored_files:
                click.echo(warning(f"  {file}"))
        else:
            for file in ignored_files[:3]:
                click.echo(warning(f"  {file}"))
            click.echo(warning(f"  ... and {len(ignored_files) - 3} more"))
        click.echo(info("Use 'lit add -f <file>' to force add ignored files"))
    
    # Warn about conflict markers still present
    if conflict_warnings:
        click.echo()
        click.echo(warning(f"Warning: {len(conflict_warnings)} file(s) still contain conflict markers:"))
        for file in conflict_warnings:
            click.echo(warning(f"  {file}"))
        click.echo(warning("Make sure you have resolved all conflicts before committing."))
    
    # Inform about merge progress
    if merge_in_progress and resolved_conflicts:
        click.echo()
        click.echo(info(f"Merge in progress: {len(resolved_conflicts)} file(s) marked as resolved"))
        click.echo(info("When all conflicts are resolved, run 'lit commit' to complete the merge"))
    
    if failed_files:
        click.echo()
        click.echo(error(f"Failed to add {len(failed_files)} file(s):"))
        for file, reason in failed_files:
            click.echo(error(f"  {file}: {reason}"))
    
    if not added_files and not failed_files and not ignored_files:
        click.echo(error("No files matched"))
