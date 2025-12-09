"""List tree contents - show object tree structure."""

import click
from lit.core.repository import Repository
from lit.core.objects import Tree, Commit, Blob
from lit.cli.output import success, error, info, warning
from colorama import Fore, Style


@click.command('ls-tree')
@click.option('-r', '--recursive', is_flag=True, help='Recurse into sub-trees')
@click.option('-t', '--tree', is_flag=True, help='Show tree entries even when going into subtrees')
@click.option('--name-only', is_flag=True, help='Show only file names')
@click.option('--abbrev', type=int, default=7, help='Abbreviate hash to N characters (default: 7)')
@click.argument('treeish', required=False, default='HEAD')
@click.argument('path', required=False)
def ls_tree_cmd(recursive, tree, name_only, abbrev, treeish, path):
    """
    List contents of a tree object.
    
    TREEISH can be a commit hash, branch name, or tag. Defaults to HEAD.
    PATH filters to show only entries under that path.
    
    Examples:
        lit ls-tree                  # Show tree for HEAD
        lit ls-tree HEAD             # Same as above
        lit ls-tree main             # Show tree for main branch
        lit ls-tree -r HEAD          # Recursively list all files
        lit ls-tree --name-only HEAD # Only show file names
        lit ls-tree HEAD src/        # Show only entries under src/
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    try:
        # Resolve treeish to commit
        commit_hash = repo.refs.resolve_reference(treeish)
        if not commit_hash:
            click.echo(error(f"Not a valid reference: {treeish}"))
            raise click.Abort()
        
        # Get commit and tree
        commit_obj = repo.read_object(commit_hash)
        if isinstance(commit_obj, Commit):
            tree_hash = commit_obj.tree
        elif isinstance(commit_obj, Tree):
            tree_hash = commit_hash
        else:
            click.echo(error(f"Not a valid tree-ish: {treeish}"))
            raise click.Abort()
        
        tree_obj = repo.read_object(tree_hash)
        if not isinstance(tree_obj, Tree):
            click.echo(error(f"Not a valid tree: {tree_hash}"))
            raise click.Abort()
        
        # Display tree entries
        display_tree(repo, tree_obj, "", recursive, tree, name_only, abbrev, path)
        
    except click.Abort:
        raise
    except Exception as e:
        click.echo(error(f"ls-tree failed: {e}"))
        import traceback
        traceback.print_exc()
        raise click.Abort()


def display_tree(repo, tree_obj, prefix, recursive, show_trees, name_only, abbrev, filter_path):
    """Display tree entries with optional recursion."""
    for entry in sorted(tree_obj.entries, key=lambda e: e.name):
        full_path = f"{prefix}{entry.name}" if prefix else entry.name
        
        # Apply path filter if specified
        if filter_path:
            filter_path = filter_path.rstrip('/')
            if not full_path.startswith(filter_path) and not filter_path.startswith(full_path):
                continue
        
        if entry.type == 'tree':
            # It's a directory
            if not recursive or show_trees:
                if name_only:
                    click.echo(f"{Fore.BLUE}{full_path}/{Style.RESET_ALL}")
                else:
                    hash_display = entry.hash[:abbrev] if abbrev else entry.hash
                    click.echo(f"{entry.mode} tree {Fore.YELLOW}{hash_display}{Style.RESET_ALL}    {Fore.BLUE}{full_path}/{Style.RESET_ALL}")
            
            if recursive:
                # Recurse into subtree
                subtree = repo.read_object(entry.hash)
                if isinstance(subtree, Tree):
                    display_tree(repo, subtree, full_path + "/", recursive, show_trees, name_only, abbrev, filter_path)
        else:
            # It's a blob (file)
            if name_only:
                click.echo(full_path)
            else:
                hash_display = entry.hash[:abbrev] if abbrev else entry.hash
                click.echo(f"{entry.mode} blob {Fore.YELLOW}{hash_display}{Style.RESET_ALL}    {full_path}")


@click.command('cat-file')
@click.option('-t', '--type', 'show_type', is_flag=True, help='Show object type')
@click.option('-s', '--size', 'show_size', is_flag=True, help='Show object size')
@click.option('-p', '--pretty', is_flag=True, help='Pretty-print object content')
@click.argument('object_hash')
def cat_file_cmd(show_type, show_size, pretty, object_hash):
    """
    Show object content, type, or size.
    
    Displays the content of a Git object (blob, tree, commit).
    
    Examples:
        lit cat-file -t abc123     # Show object type
        lit cat-file -s abc123     # Show object size
        lit cat-file -p abc123     # Pretty-print object content
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    try:
        # Try to resolve short hash
        full_hash = resolve_short_hash(repo, object_hash)
        if not full_hash:
            click.echo(error(f"Object not found: {object_hash}"))
            raise click.Abort()
        
        obj = repo.read_object(full_hash)
        
        if show_type:
            if isinstance(obj, Commit):
                click.echo("commit")
            elif isinstance(obj, Tree):
                click.echo("tree")
            elif isinstance(obj, Blob):
                click.echo("blob")
            else:
                click.echo("unknown")
            return
        
        if show_size:
            if isinstance(obj, Commit):
                content = obj.serialize()
            elif isinstance(obj, Tree):
                content = obj.serialize()
            elif isinstance(obj, Blob):
                content = obj.data
            else:
                content = b""
            click.echo(len(content))
            return
        
        if pretty:
            if isinstance(obj, Commit):
                click.echo(f"{Fore.YELLOW}tree {obj.tree}{Style.RESET_ALL}")
                for parent in obj.parents:
                    click.echo(f"{Fore.YELLOW}parent {parent}{Style.RESET_ALL}")
                click.echo(f"author {obj.author} {obj.author_time} {obj.author_timezone}")
                click.echo(f"committer {obj.committer} {obj.committer_time} {obj.committer_timezone}")
                click.echo()
                click.echo(obj.message)
            elif isinstance(obj, Tree):
                for entry in obj.entries:
                    type_str = "tree" if entry.type == "tree" else "blob"
                    click.echo(f"{entry.mode} {type_str} {Fore.YELLOW}{entry.hash}{Style.RESET_ALL}    {entry.name}")
            elif isinstance(obj, Blob):
                try:
                    click.echo(obj.data.decode('utf-8'))
                except:
                    click.echo(f"<binary data: {len(obj.data)} bytes>")
            return
        
        # Default: raw content
        if isinstance(obj, Blob):
            try:
                click.echo(obj.data.decode('utf-8'))
            except:
                click.echo(f"<binary data: {len(obj.data)} bytes>")
        else:
            click.echo(error("Use -p to pretty-print non-blob objects"))
            
    except click.Abort:
        raise
    except Exception as e:
        click.echo(error(f"cat-file failed: {e}"))
        raise click.Abort()


def resolve_short_hash(repo, short_hash):
    """Resolve a short hash to full hash."""
    if len(short_hash) == 40:
        return short_hash
    
    objects_dir = repo.objects_dir
    matches = []
    
    if len(short_hash) >= 2:
        subdir = objects_dir / short_hash[:2]
        if subdir.exists():
            for obj_file in subdir.iterdir():
                full_hash = short_hash[:2] + obj_file.name
                if full_hash.startswith(short_hash):
                    matches.append(full_hash)
    
    if len(matches) == 1:
        return matches[0]
    return None


@click.command('count-objects')
@click.option('-v', '--verbose', is_flag=True, help='Show detailed information')
def count_objects_cmd(verbose):
    """
    Count objects in the repository.
    
    Shows statistics about loose objects in the object database.
    
    Examples:
        lit count-objects          # Show object counts
        lit count-objects -v       # Show detailed breakdown
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    objects_dir = repo.objects_dir
    
    total_objects = 0
    total_size = 0
    type_counts = {'commit': 0, 'tree': 0, 'blob': 0, 'unknown': 0}
    
    for subdir in objects_dir.iterdir():
        if subdir.is_dir() and len(subdir.name) == 2:
            for obj_file in subdir.iterdir():
                total_objects += 1
                total_size += obj_file.stat().st_size
                
                if verbose:
                    # Read object to determine type
                    full_hash = subdir.name + obj_file.name
                    try:
                        obj = repo.read_object(full_hash)
                        if isinstance(obj, Commit):
                            type_counts['commit'] += 1
                        elif isinstance(obj, Tree):
                            type_counts['tree'] += 1
                        elif isinstance(obj, Blob):
                            type_counts['blob'] += 1
                        else:
                            type_counts['unknown'] += 1
                    except:
                        type_counts['unknown'] += 1
    
    if verbose:
        click.echo(f"{Fore.CYAN}Object Statistics:{Style.RESET_ALL}")
        click.echo(f"  Commits: {Fore.YELLOW}{type_counts['commit']}{Style.RESET_ALL}")
        click.echo(f"  Trees:   {Fore.YELLOW}{type_counts['tree']}{Style.RESET_ALL}")
        click.echo(f"  Blobs:   {Fore.YELLOW}{type_counts['blob']}{Style.RESET_ALL}")
        if type_counts['unknown'] > 0:
            click.echo(f"  Unknown: {type_counts['unknown']}")
        click.echo()
    
    size_kb = total_size / 1024
    click.echo(f"{total_objects} objects, {size_kb:.2f} KB")
