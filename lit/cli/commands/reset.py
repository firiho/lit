"""Reset command - reset current HEAD to a specified state."""

import click
from pathlib import Path
from lit.core.repository import Repository
from lit.core.objects import Commit, Tree, Blob
from lit.core.index import Index
from lit.cli.output import success, error, info, warning


def get_tree_files(repo, tree, prefix=''):
    """Recursively get all files from tree."""
    files = {}
    
    if not tree:
        return files
    
    for entry in tree.entries:
        path = f"{prefix}{entry.name}" if prefix else entry.name
        
        if entry.type == 'blob':
            files[path] = entry.hash
        elif entry.type == 'tree':
            subtree = repo.read_object(entry.hash)
            if isinstance(subtree, Tree):
                subfiles = get_tree_files(repo, subtree, f"{path}/")
                files.update(subfiles)
    
    return files


def reset_index_to_tree(repo, tree_hash):
    """
    Reset the index to match a tree.
    
    Args:
        repo: Repository instance
        tree_hash: Hash of tree to reset index to
    
    Returns:
        Number of entries in the new index
    """
    tree = repo.read_object(tree_hash)
    if not isinstance(tree, Tree):
        raise ValueError("Not a valid tree")
    
    # Get all files from tree
    tree_files = get_tree_files(repo, tree)
    
    # Create new index from tree
    index = Index()
    
    for file_path, blob_hash in tree_files.items():
        # Get blob to determine mode
        blob = repo.read_object(blob_hash)
        if isinstance(blob, Blob):
            # Add entry directly to index
            # We need to create an IndexEntry manually
            from lit.core.index import IndexEntry
            import time
            
            # Create a basic entry with the blob hash
            entry = IndexEntry(
                ctime=int(time.time()),
                ctime_ns=0,
                mtime=int(time.time()),
                mtime_ns=0,
                dev=0,
                ino=0,
                mode=0o100644,  # Regular file
                uid=0,
                gid=0,
                size=len(blob.data),
                sha1=blob_hash,
                flags=len(file_path) if len(file_path) < 0xFFF else 0xFFF,
                path=file_path
            )
            index.entries[file_path] = entry
    
    # Write the new index
    index.write(str(repo.index_file))
    
    return len(index.entries)


def reset_files_in_index(repo, tree_hash, file_paths):
    """
    Reset specific files in the index to match a tree.
    
    This is used for 'lit reset HEAD <file>' to unstage files.
    
    Args:
        repo: Repository instance
        tree_hash: Hash of tree to get file versions from
        file_paths: List of file paths to reset
    
    Returns:
        Tuple of (reset_count, not_found_count)
    """
    tree = repo.read_object(tree_hash)
    if not isinstance(tree, Tree):
        raise ValueError("Not a valid tree")
    
    # Get all files from tree
    tree_files = get_tree_files(repo, tree)
    
    # Load current index
    index = Index()
    if repo.index_file.exists():
        index.read(str(repo.index_file))
    
    reset_count = 0
    removed_count = 0
    
    for file_path in file_paths:
        # Normalize path
        file_path = str(file_path).replace('\\', '/')
        if file_path.startswith('./'):
            file_path = file_path[2:]
        
        if file_path in tree_files:
            # File exists in tree - reset index entry to tree version
            blob_hash = tree_files[file_path]
            blob = repo.read_object(blob_hash)
            if isinstance(blob, Blob):
                from lit.core.index import IndexEntry
                import time
                
                entry = IndexEntry(
                    ctime=int(time.time()),
                    ctime_ns=0,
                    mtime=int(time.time()),
                    mtime_ns=0,
                    dev=0,
                    ino=0,
                    mode=0o100644,
                    uid=0,
                    gid=0,
                    size=len(blob.data),
                    sha1=blob_hash,
                    flags=len(file_path) if len(file_path) < 0xFFF else 0xFFF,
                    path=file_path
                )
                index.entries[file_path] = entry
                reset_count += 1
        else:
            # File doesn't exist in tree - remove from index (unstage new file)
            if file_path in index.entries:
                del index.entries[file_path]
                removed_count += 1
    
    # Write the updated index
    index.write(str(repo.index_file))
    
    return reset_count, removed_count


def reset_working_tree_to_tree(repo, tree_hash):
    """
    Reset the working tree to match a tree.
    
    Args:
        repo: Repository instance
        tree_hash: Hash of tree to reset working tree to
    
    Returns:
        Number of files updated
    """
    tree = repo.read_object(tree_hash)
    if not isinstance(tree, Tree):
        raise ValueError("Not a valid tree")
    
    # Get all files from tree
    tree_files = get_tree_files(repo, tree)
    
    # Get current files in working directory
    work_tree = repo.work_tree
    existing_files = set()
    for path in work_tree.rglob('*'):
        if path.is_file():
            rel_path = path.relative_to(work_tree)
            if not any(part.startswith('.') for part in rel_path.parts):
                existing_files.add(str(rel_path))
    
    # Remove files not in the new tree
    removed = 0
    for file_path in existing_files:
        if file_path not in tree_files:
            full_path = work_tree / file_path
            try:
                full_path.unlink()
                removed += 1
            except:
                pass
    
    # Write all files from tree
    written = 0
    for file_path, blob_hash in tree_files.items():
        full_path = work_tree / file_path
        
        # Create directory if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read blob and write to file
        blob = repo.read_object(blob_hash)
        if isinstance(blob, Blob):
            full_path.write_bytes(blob.data)
            written += 1
    
    return written


def update_head_ref(repo, commit_hash):
    """
    Update HEAD (or the branch it points to) to a new commit.
    
    Args:
        repo: Repository instance
        commit_hash: New commit hash
    """
    head_file = repo.head_file
    
    if not head_file.exists():
        # No HEAD, just set it directly
        head_file.write_text(commit_hash + '\n')
        return
    
    head_content = head_file.read_text().strip()
    
    if head_content.startswith('ref: '):
        # Symbolic reference - update the branch
        ref_path = head_content[5:]
        ref_file = repo.lit_dir / ref_path
        ref_file.parent.mkdir(parents=True, exist_ok=True)
        ref_file.write_text(commit_hash + '\n')
    else:
        # Detached HEAD - update HEAD directly
        head_file.write_text(commit_hash + '\n')


@click.command('reset')
@click.argument('commit', default='HEAD')
@click.argument('paths', nargs=-1, type=click.Path())
@click.option('--soft', is_flag=True, help='Only move HEAD, keep index and working tree')
@click.option('--mixed', is_flag=True, help='Move HEAD and reset index, keep working tree (default)')
@click.option('--hard', is_flag=True, help='Move HEAD, reset index and working tree (DESTRUCTIVE)')
def reset_cmd(commit, paths, soft, mixed, hard):
    """
    Reset current HEAD to a specified state, or unstage files.
    
    When paths are given, reset those files in the index to match
    the specified commit (default HEAD), without moving HEAD.
    This is used to unstage files.
    
    When no paths are given, move HEAD (and the current branch) to 
    the specified commit, optionally resetting index and/or working tree.
    
    Modes (only apply when no paths given):
        --soft   Keep index and working tree unchanged
        --mixed  Reset index but keep working tree (default)
        --hard   Reset both index and working tree (DESTRUCTIVE!)
    
    COMMIT can be:
        - A commit hash (full or abbreviated)
        - A branch name
        - HEAD~N to go back N commits
        - HEAD^ to go back one commit
    
    Examples:
        lit reset HEAD file.txt    # Unstage file.txt
        lit reset file.txt         # Unstage file.txt (same as above)
        lit reset HEAD~1           # Undo last commit, keep changes staged
        lit reset --soft HEAD~1    # Undo last commit, keep changes staged  
        lit reset --mixed HEAD~1   # Undo last commit, unstage changes
        lit reset --hard HEAD~1    # Undo last commit, discard all changes
        lit reset --hard           # Discard all uncommitted changes
        lit reset abc123           # Reset to specific commit
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    refs_mgr = repo.refs
    
    # Determine if we're resetting files or the whole HEAD
    # If 'commit' looks like a file path and exists, treat it as a path
    all_paths = list(paths)
    actual_commit = commit
    
    # Check if 'commit' argument is actually a file path
    commit_path = Path(commit)
    is_file_path = False
    
    if commit != 'HEAD' and not commit.startswith('HEAD~') and not commit.startswith('HEAD^'):
        # Check if it's an existing file or staged file
        if commit_path.exists() or (commit_path.is_absolute() == False and (repo.work_tree / commit).exists()):
            is_file_path = True
        else:
            # Check if it's in the index
            index = Index()
            if repo.index_file.exists():
                index.read(str(repo.index_file))
            if commit in index.entries or commit.lstrip('./') in index.entries:
                is_file_path = True
        
        # Also check if it doesn't look like a valid ref
        if is_file_path or (not refs_mgr.resolve_reference(commit) and '/' not in commit and len(commit) < 40):
            # Likely a file path, not a commit
            if commit_path.exists() or commit in (index.entries if 'index' in dir() else {}):
                is_file_path = True
    
    if is_file_path:
        all_paths = [commit] + list(paths)
        actual_commit = 'HEAD'
    
    # If we have file paths, do file-specific reset (unstage)
    if all_paths:
        if soft or hard:
            click.echo(error("Cannot use --soft or --hard with file paths"))
            click.echo(info("Use 'lit reset <file>' to unstage files"))
            raise click.Abort()
        
        # Resolve the commit to get its tree
        commit_hash = refs_mgr.resolve_reference(actual_commit)
        if not commit_hash:
            # For HEAD with no commits, just remove from index
            commit_hash = refs_mgr.resolve_head()
        
        if not commit_hash:
            # No commits yet - just remove files from index
            index = Index()
            if repo.index_file.exists():
                index.read(str(repo.index_file))
            
            removed = 0
            for file_path in all_paths:
                normalized = str(file_path).replace('\\', '/').lstrip('./')
                if normalized in index.entries:
                    del index.entries[normalized]
                    removed += 1
                    click.echo(info(f"Unstaged: {normalized}"))
            
            if removed > 0:
                index.write(str(repo.index_file))
                click.echo(success(f"Unstaged {removed} file(s)"))
            else:
                click.echo(warning("No files were unstaged"))
            return
        
        # Get the commit's tree
        try:
            commit_obj = repo.read_object(commit_hash)
            if not isinstance(commit_obj, Commit):
                click.echo(error(f"Not a valid commit: {commit_hash[:7]}"))
                raise click.Abort()
            
            reset_count, removed_count = reset_files_in_index(repo, commit_obj.tree, all_paths)
            
            total = reset_count + removed_count
            if total > 0:
                if reset_count > 0:
                    click.echo(success(f"Reset {reset_count} file(s) to {actual_commit}"))
                if removed_count > 0:
                    click.echo(success(f"Unstaged {removed_count} new file(s)"))
            else:
                click.echo(warning("No files were reset"))
                
        except Exception as e:
            click.echo(error(f"Reset failed: {e}"))
            raise click.Abort()
        
        return
    
    # Full reset (no file paths) - original logic
    # Validate only one mode is specified
    mode_count = sum([soft, mixed, hard])
    if mode_count > 1:
        click.echo(error("Cannot specify multiple reset modes"))
        raise click.Abort()
    
    # Default to mixed mode
    if mode_count == 0:
        mixed = True
    
    # Handle special syntax: HEAD~N and HEAD^
    target = actual_commit
    if target.startswith('HEAD~') or target.startswith('HEAD^'):
        # Count how many commits to go back
        if target.startswith('HEAD~'):
            try:
                steps = int(target[5:]) if len(target) > 5 else 1
            except ValueError:
                click.echo(error(f"Invalid revision: {target}"))
                raise click.Abort()
        else:  # HEAD^
            steps = target.count('^')
        
        # Walk back from HEAD
        current_hash = refs_mgr.resolve_head()
        if not current_hash:
            click.echo(error("No commits yet"))
            raise click.Abort()
        
        for i in range(steps):
            commit_obj = repo.read_object(current_hash)
            if not isinstance(commit_obj, Commit):
                click.echo(error(f"Not a valid commit: {current_hash[:7]}"))
                raise click.Abort()
            
            if not commit_obj.parents:
                click.echo(error(f"Cannot go back {steps} commits - reached root commit"))
                raise click.Abort()
            
            current_hash = commit_obj.parents[0]
        
        commit_hash = current_hash
    else:
        # Regular reference resolution
        commit_hash = refs_mgr.resolve_reference(target)
        if not commit_hash:
            click.echo(error(f"Unknown revision: {target}"))
            raise click.Abort()
    
    # Read the target commit
    try:
        commit_obj = repo.read_object(commit_hash)
        if not isinstance(commit_obj, Commit):
            click.echo(error(f"Not a valid commit: {commit_hash[:7]}"))
            raise click.Abort()
    except Exception as e:
        click.echo(error(f"Cannot read commit: {e}"))
        raise click.Abort()
    
    # Get current HEAD for comparison
    current_head = refs_mgr.resolve_head()
    
    # Perform the reset
    try:
        if soft:
            # Soft: Only move HEAD
            update_head_ref(repo, commit_hash)
            click.echo(success(f"HEAD is now at {commit_hash[:7]}"))
            click.echo(info("Index and working tree unchanged"))
            
        elif mixed:
            # Mixed: Move HEAD and reset index
            update_head_ref(repo, commit_hash)
            entry_count = reset_index_to_tree(repo, commit_obj.tree)
            click.echo(success(f"HEAD is now at {commit_hash[:7]}"))
            click.echo(info(f"Index reset ({entry_count} entries)"))
            click.echo(info("Working tree unchanged - use 'lit status' to see unstaged changes"))
            
        elif hard:
            # Hard: Move HEAD, reset index, and reset working tree
            click.echo(warning("Performing hard reset - uncommitted changes will be lost!"))
            update_head_ref(repo, commit_hash)
            reset_index_to_tree(repo, commit_obj.tree)
            file_count = reset_working_tree_to_tree(repo, commit_obj.tree)
            click.echo(success(f"HEAD is now at {commit_hash[:7]}"))
            click.echo(info(f"Index and working tree reset ({file_count} files)"))
        
        # Show commit info
        message_first_line = commit_obj.message.split('\n')[0]
        click.echo(info(f"Commit: {message_first_line}"))
        
    except Exception as e:
        click.echo(error(f"Reset failed: {e}"))
        raise click.Abort()
