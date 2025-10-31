"""Status command - show working tree status."""

import click
from pathlib import Path
from lit.core.repository import Repository
from lit.core.index import Index
from lit.core.objects import Commit, Tree
from lit.cli.output import success, error, info, warning
from colorama import Fore, Style


def get_head_tree(repo):
    """Get tree from HEAD commit."""
    head_file = repo.head_file
    
    if not head_file.exists():
        return None
    
    head_content = head_file.read_text().strip()
    
    if head_content.startswith('ref: '):
        ref_path = head_content[5:]
        ref_file = repo.lit_dir / ref_path
        
        if not ref_file.exists():
            return None
        
        commit_hash = ref_file.read_text().strip()
    else:
        commit_hash = head_content
    
    try:
        commit = repo.read_object(commit_hash)
        if isinstance(commit, Commit):
            tree = repo.read_object(commit.tree)
            return tree if isinstance(tree, Tree) else None
    except:
        return None
    
    return None


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


def get_working_files(repo):
    """Get all files in working directory with their blob hashes."""
    from lit.core.objects import Blob
    
    files = {}
    work_tree = repo.work_tree
    
    for path in work_tree.rglob('*'):
        if path.is_file():
            rel_path = path.relative_to(work_tree)
            
            if any(part.startswith('.') for part in rel_path.parts):
                continue
            
            try:
                # Read file and create blob to get proper hash
                with open(path, 'rb') as f:
                    data = f.read()
                blob = Blob(data)
                files[str(rel_path)] = blob.hash
            except:
                pass
    
    return files


@click.command('status')
def status_cmd():
    """
    Show the working tree status.
    
    Displays:
    - Changes staged for commit (in index)
    - Changes not staged for commit (modified files)
    - Untracked files (new files not in index)
    
    Examples:
        lit status
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    # Get HEAD tree files
    head_tree = get_head_tree(repo)
    head_files = get_tree_files(repo, head_tree) if head_tree else {}
    
    # Get index files
    index = Index()
    index_file = repo.index_file
    if index_file.exists():
        index.read(str(index_file))
    index_files = {entry.path: entry.sha1 for entry in index.entries.values()}
    
    # Get working directory files
    working_files = get_working_files(repo)
    
    # Calculate differences
    staged_new = []
    staged_modified = []
    staged_deleted = []
    
    unstaged_modified = []
    unstaged_deleted = []
    
    untracked = []
    
    # Check staged changes (index vs HEAD)
    for path, index_hash in index_files.items():
        if path not in head_files:
            staged_new.append(path)
        elif head_files[path] != index_hash:
            staged_modified.append(path)
    
    for path in head_files:
        if path not in index_files:
            # File removed from index = staged for deletion
            staged_deleted.append(path)
    
    # Check unstaged changes (working vs index)
    for path, working_hash in working_files.items():
        if path in index_files:
            # File is in index - check if modified
            if index_files[path] != working_hash:
                unstaged_modified.append(path)
        elif path in head_files:
            # File is in HEAD but not in index
            if head_files[path] != working_hash:
                unstaged_modified.append(path)
        else:
            # File is not in index or HEAD - it's untracked
            untracked.append(path)
    
    # Check for deleted files (in index but not in working directory)
    for path in index_files:
        if path not in working_files:
            unstaged_deleted.append(path)
    
    # Display status
    refs_mgr = repo.refs
    
    if refs_mgr.is_detached_head():
        # Detached HEAD state
        commit_hash = refs_mgr.resolve_head()
        click.echo(f"{Fore.YELLOW}HEAD detached at {commit_hash[:7]}{Style.RESET_ALL}")
    else:
        # On a branch
        branch = refs_mgr.get_current_branch() or "main"
        click.echo(f"On branch {Fore.CYAN}{branch}{Style.RESET_ALL}")
    
    click.echo()
    
    # Show staged changes
    has_staged = staged_new or staged_modified or staged_deleted
    if has_staged:
        click.echo(Fore.GREEN + "Changes to be committed:" + Style.RESET_ALL)
        click.echo(info("  (use \"lit reset HEAD <file>...\" to unstage)"))
        click.echo()
        
        for path in sorted(staged_new):
            click.echo(f"  {Fore.GREEN}new file:   {path}{Style.RESET_ALL}")
        for path in sorted(staged_modified):
            click.echo(f"  {Fore.GREEN}modified:   {path}{Style.RESET_ALL}")
        for path in sorted(staged_deleted):
            click.echo(f"  {Fore.GREEN}deleted:    {path}{Style.RESET_ALL}")
        
        click.echo()
    
    # Show unstaged changes
    has_unstaged = unstaged_modified or unstaged_deleted
    if has_unstaged:
        click.echo(Fore.YELLOW + "Changes not staged for commit:" + Style.RESET_ALL)
        click.echo(info("  (use \"lit add <file>...\" to update what will be committed)"))
        click.echo()
        
        for path in sorted(unstaged_modified):
            click.echo(f"  {Fore.YELLOW}modified:   {path}{Style.RESET_ALL}")
        for path in sorted(unstaged_deleted):
            click.echo(f"  {Fore.YELLOW}deleted:    {path}{Style.RESET_ALL}")

        click.echo()
    
    # Show untracked files
    if untracked:
        click.echo(Fore.RED + "Untracked files:" + Style.RESET_ALL)
        click.echo(info("  (use \"lit add <file>...\" to include in what will be committed)"))
        click.echo()
        
        for path in sorted(untracked):
            click.echo(f"  {Fore.RED}{path}{Style.RESET_ALL}")
        
        click.echo()
    
    # Show clean message
    if not has_staged and not has_unstaged and not untracked:
        click.echo(success("Nothing to commit, working tree clean"))
    elif not has_staged and (has_unstaged or untracked):
        click.echo(info("No changes added to commit (use \"lit add\")"))
