"""Diff command - show changes between commits, working tree, and index."""

import click
from lit.core.repository import Repository
from lit.cli.output import success, error, info, warning
from colorama import Fore, Style


@click.command('diff')
@click.option('--staged', '--cached', is_flag=True, help='Show changes staged for commit (index vs HEAD)')
@click.option('--no-color', is_flag=True, help='Disable colored output')
@click.argument('commit1', required=False)
@click.argument('commit2', required=False)
def diff_cmd(staged, no_color, commit1, commit2):
    """
    Show changes between commits, working tree, and index.
    
    With no arguments, shows unstaged changes (working tree vs index).
    With --staged, shows staged changes (index vs HEAD).
    With one commit, shows changes between that commit and working tree.
    With two commits, shows changes between those commits.
    
    Examples:
        lit diff                    # Unstaged changes (working vs index)
        lit diff --staged           # Staged changes (index vs HEAD)
        lit diff HEAD               # Working tree vs HEAD
        lit diff abc123             # Working tree vs commit abc123
        lit diff abc123 def456      # Changes between two commits
        lit diff main feature       # Changes between branches
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    diff_engine = repo.diff
    use_color = not no_color
    
    try:
        if commit2:
            # Two commits specified - diff between them
            refs_mgr = repo.refs
            
            # Resolve commit hashes
            hash1 = refs_mgr.resolve_reference(commit1)
            if not hash1:
                click.echo(error(f"Not a valid reference: {commit1}"))
                raise click.Abort()
            
            hash2 = refs_mgr.resolve_reference(commit2)
            if not hash2:
                click.echo(error(f"Not a valid reference: {commit2}"))
                raise click.Abort()
            
            diffs = diff_engine.diff_commits(hash1, hash2)
            
        elif commit1:
            # One commit specified - diff working tree vs commit
            refs_mgr = repo.refs
            commit_hash = refs_mgr.resolve_reference(commit1)
            
            if not commit_hash:
                click.echo(error(f"Not a valid reference: {commit1}"))
                raise click.Abort()
            
            # Get commit tree files
            from lit.core.objects import Commit, Tree
            commit_obj = repo.read_object(commit_hash)
            if not isinstance(commit_obj, Commit):
                click.echo(error(f"Not a valid commit: {commit1}"))
                raise click.Abort()
            
            tree = repo.read_object(commit_obj.tree)
            if not isinstance(tree, Tree):
                click.echo(error(f"Invalid tree in commit: {commit1}"))
                raise click.Abort()
            
            commit_files = diff_engine._get_tree_files(tree)
            
            # Get working directory files
            from pathlib import Path
            work_tree = repo.work_tree
            working_files = {}
            
            for path in work_tree.rglob('*'):
                if path.is_file():
                    rel_path = path.relative_to(work_tree)
                    
                    if any(part.startswith('.') for part in rel_path.parts):
                        continue
                    
                    try:
                        working_files[str(rel_path)] = path.read_bytes()
                    except:
                        pass
            
            # Compute diffs
            diffs = []
            all_paths = set(commit_files.keys()) | set(working_files.keys())
            
            for path in sorted(all_paths):
                commit_hash = commit_files.get(path)
                working_content = working_files.get(path)
                
                # Get old content
                old_content = None
                if commit_hash:
                    try:
                        old_blob = repo.read_object(commit_hash)
                        old_content = old_blob.data
                    except:
                        pass
                
                # Skip if unchanged
                if old_content == working_content:
                    continue
                
                diff = diff_engine.diff_blobs(path, old_content, working_content)
                diffs.append(diff)
            
        elif staged:
            # Staged changes (index vs HEAD)
            diffs = diff_engine.diff_index_to_head()
        else:
            # Default: unstaged changes (working vs index)
            diffs = diff_engine.diff_working_to_index()
        
        # Format and display
        if not diffs:
            click.echo(info("No changes to display"))
            return
        
        output = diff_engine.format_diff(diffs, color=use_color)
        click.echo(output)
        
    except click.Abort:
        raise
    except Exception as e:
        click.echo(error(f"Diff failed: {e}"))
        import traceback
        traceback.print_exc()
        raise click.Abort()
