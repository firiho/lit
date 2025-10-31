"""Commit command - create a commit from staged changes."""

import click
import os
import configparser
from pathlib import Path
from lit.core.repository import Repository
from lit.core.index import Index
from lit.core.objects import Tree, Commit
from lit.cli.output import success, error, info, warning


def get_author_info():
    """Get author name and email from environment, config, or prompt."""
    name = os.environ.get('LIT_AUTHOR_NAME') or os.environ.get('GIT_AUTHOR_NAME')
    email = os.environ.get('LIT_AUTHOR_EMAIL') or os.environ.get('GIT_AUTHOR_EMAIL')
    
    if not name or not email:
        config = configparser.ConfigParser()
        
        repo = Repository.find_repository()
        if repo and repo.config_file.exists():
            config.read(repo.config_file)
        
        global_config = Path.home() / '.litconfig'
        if global_config.exists():
            config.read(global_config)
        
        if not name and config.has_option('user', 'name'):
            name = config.get('user', 'name')
        if not email and config.has_option('user', 'email'):
            email = config.get('user', 'email')
    
    # If still missing, prompt user and save to repo config
    if not name or not email:
        import click
        from lit.cli.output import warning, info
        
        click.echo()
        click.echo(warning("Author information not configured"))
        click.echo(info("Please provide your name and email for this commit."))
        click.echo(info("This will be saved to the repository config."))
        click.echo()
        click.echo(info("Tip: Use 'lit config set --global user.name \"Your Name\"' to set globally"))
        click.echo()
        
        if not name:
            name = input("Your name: ").strip()
            while not name:
                name = input("Name cannot be empty. Your name: ").strip()
        
        if not email:
            email = input("Your email: ").strip()
            while not email or '@' not in email:
                email = input("Invalid email. Your email: ").strip()
        
        # Save to repository config
        repo = Repository.find_repository()
        if repo:
            config_file = repo.config_file
            repo_config = configparser.ConfigParser()
            if config_file.exists():
                repo_config.read(config_file)
            
            if not repo_config.has_section('user'):
                repo_config.add_section('user')
            
            repo_config.set('user', 'name', name)
            repo_config.set('user', 'email', email)
            
            with open(config_file, 'w') as f:
                repo_config.write(f)
            
            click.echo()
            click.echo(info(f"✓ Saved to repository config: {name} <{email}>"))
            click.echo(info("You won't be asked again in this repository."))
            click.echo()
    
    return f"{name} <{email}>"


def build_tree_from_index(repo, index):
    """
    Build tree object from index entries.
    
    Creates a tree structure matching the index, handling nested directories.
    """
    from collections import defaultdict
    
    trees = defaultdict(Tree)
    
    for path in sorted(index.entries.keys()):
        entry = index.entries[path]
        parts = Path(path).parts
        
        for i in range(len(parts)):
            dir_path = str(Path(*parts[:i])) if i > 0 else ''
            trees[dir_path]
        
        dir_path = str(Path(*parts[:-1])) if len(parts) > 1 else ''
        filename = parts[-1]
        
        mode = '100755' if entry.mode & 0o111 else '100644'
        trees[dir_path].add_entry(mode, 'blob', entry.sha1, filename)
    
    for dir_path in sorted(trees.keys(), key=lambda x: x.count('/'), reverse=True):
        if dir_path:
            tree = trees[dir_path]
            tree_hash = repo.write_object(tree)
            
            parent_parts = Path(dir_path).parts
            parent_path = str(Path(*parent_parts[:-1])) if len(parent_parts) > 1 else ''
            dir_name = parent_parts[-1]
            
            trees[parent_path].add_entry('040000', 'tree', tree_hash, dir_name)
    
    root_tree = trees['']
    tree_hash = repo.write_object(root_tree)
    return tree_hash


def get_parent_commit(repo):
    """Get hash of current HEAD commit, if any."""
    head_file = repo.head_file
    
    if not head_file.exists():
        return None
    
    head_content = head_file.read_text().strip()
    
    if head_content.startswith('ref: '):
        ref_path = head_content[5:]
        ref_file = repo.lit_dir / ref_path
        
        if ref_file.exists():
            return ref_file.read_text().strip()
    else:
        return head_content
    
    return None


def update_ref(repo, ref_name, commit_hash):
    """Update a reference to point to commit."""
    ref_file = repo.lit_dir / ref_name
    ref_file.parent.mkdir(parents=True, exist_ok=True)
    ref_file.write_text(commit_hash + '\n')


@click.command('commit')
@click.option('-m', '--message', required=True, help='Commit message')
@click.option('--author', help='Author name and email (format: "Name <email>")')
def commit_cmd(message, author):
    """
    Record changes to the repository.
    
    Creates a commit from the staged changes in the index.
    A commit captures a snapshot of the project at a point in time.
    
    Examples:
        lit commit -m "Initial commit"
        lit commit -m "Add feature" --author "Jane <jane@example.com>"
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    index = Index()
    index_file = repo.index_file
    
    if not index_file.exists():
        click.echo(error("Nothing to commit (staging area is empty)"))
        click.echo(info("Use 'lit add <file>' to stage changes"))
        raise click.Abort()
    
    index.read(str(index_file))
    
    if len(index) == 0:
        click.echo(error("Nothing to commit (staging area is empty)"))
        click.echo(info("Use 'lit add <file>' to stage changes"))
        raise click.Abort()
    
    if not author:
        author = get_author_info()
    
    try:
        click.echo(info(f"Building tree from {len(index)} staged file(s)..."))
        tree_hash = build_tree_from_index(repo, index)
        
        parent = get_parent_commit(repo)
        parent_list = [parent] if parent else []
        
        commit = Commit.create(
            tree_hash=tree_hash,
            parent_hashes=parent_list,
            author=author,
            committer=author,
            message=message
        )
        
        commit_hash = repo.write_object(commit)
        
        head_content = repo.head_file.read_text().strip()
        if head_content.startswith('ref: '):
            ref_name = head_content[5:]
            update_ref(repo, ref_name, commit_hash)
        else:
            repo.head_file.write_text(commit_hash + '\n')
        
        click.echo()
        click.echo(success(f"Created commit {commit_hash[:7]}"))
        click.echo(info(f"Author: {author}"))
        click.echo(info(f"Message: {message}"))
        
        if parent:
            click.echo(info(f"Parent: {parent[:7]}"))
        else:
            click.echo(info("(root commit)"))
        
        click.echo(info(f"Tree: {tree_hash[:7]}"))
        click.echo(info(f"Files: {len(index)}"))
        
        # Note: Index is NOT cleared after commit.
        # It should continue to reflect the committed state (match HEAD).
        # This is how Git works - index represents staged area.
        
    except Exception as e:
        click.echo(error(f"Failed to create commit: {e}"))
        raise click.Abort()
