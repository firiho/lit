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
    """Get author name and email from environment, config, or prompt.
    
    Priority order (highest to lowest):
    1. Environment variables (LIT_AUTHOR_NAME/EMAIL or GIT_AUTHOR_NAME/EMAIL)
    2. Repository-local config (.lit/config)
    3. Global config (~/.litconfig)
    """
    name = os.environ.get('LIT_AUTHOR_NAME') or os.environ.get('GIT_AUTHOR_NAME')
    email = os.environ.get('LIT_AUTHOR_EMAIL') or os.environ.get('GIT_AUTHOR_EMAIL')
    
    if not name or not email:
        # Read global config first (lower priority)
        global_config_path = Path.home() / '.litconfig'
        global_name = None
        global_email = None
        
        if global_config_path.exists():
            global_config = configparser.ConfigParser()
            global_config.read(global_config_path)
            if global_config.has_option('user', 'name'):
                global_name = global_config.get('user', 'name')
            if global_config.has_option('user', 'email'):
                global_email = global_config.get('user', 'email')
        
        # Read repo config second (higher priority - overrides global)
        repo = Repository.find_repository()
        repo_name = None
        repo_email = None
        
        if repo and repo.config_file.exists():
            repo_config = configparser.ConfigParser()
            repo_config.read(repo.config_file)
            if repo_config.has_option('user', 'name'):
                repo_name = repo_config.get('user', 'name')
            if repo_config.has_option('user', 'email'):
                repo_email = repo_config.get('user', 'email')
        
        # Use repo config if available, otherwise fall back to global
        if not name:
            name = repo_name or global_name
        if not email:
            email = repo_email or global_email
    
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
@click.option('-m', '--message', help='Commit message')
@click.option('--author', help='Author name and email (format: "Name <email>")')
def commit_cmd(message, author):
    """
    Record changes to the repository.
    
    Creates a commit from the staged changes in the index.
    A commit captures a snapshot of the project at a point in time.
    
    During a merge, this command completes the merge by creating a merge commit.
    
    Examples:
        lit commit -m "Initial commit"
        lit commit -m "Add feature" --author "Jane <jane@example.com>"
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    # Check if merge is in progress
    merge_in_progress = repo.merge.is_merge_in_progress()
    merge_head = repo.merge.get_merge_head() if merge_in_progress else None
    
    # Handle message for merge commits
    if not message:
        if merge_in_progress:
            # Use default merge message or from MERGE_MSG
            merge_msg_file = repo.lit_dir / 'MERGE_MSG'
            if merge_msg_file.exists():
                # Read and use a clean merge message
                current_branch = repo.refs.get_current_branch() or 'HEAD'
                message = f"Merge commit"
            else:
                message = "Merge commit"
            click.echo(info(f"Using default merge message: {message}"))
        else:
            click.echo(error("Commit message required. Use -m \"message\""))
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
        
        # If merge is in progress, add MERGE_HEAD as second parent
        if merge_in_progress and merge_head:
            parent_list.append(merge_head)
            click.echo(info(f"Creating merge commit with parents: {parent[:7]}, {merge_head[:7]}"))
        
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
        
        # Clear merge state if merge was in progress
        if merge_in_progress:
            repo.merge.clear_merge_state()
            click.echo()
            click.echo(success(f"Merge completed! Created merge commit {commit_hash[:7]}"))
        else:
            click.echo()
            click.echo(success(f"Created commit {commit_hash[:7]}"))
        
        click.echo(info(f"Author: {author}"))
        click.echo(info(f"Message: {message}"))
        
        if len(parent_list) > 1:
            click.echo(info(f"Parents: {', '.join(p[:7] for p in parent_list)}"))
        elif parent:
            click.echo(info(f"Parent: {parent[:7]}"))
        else:
            click.echo(info("(root commit)"))
        
        click.echo(info(f"Tree: {tree_hash[:7]}"))
        click.echo(info(f"Files: {len(index)}"))
        
        # Note: Index is NOT cleared after commit.
        # It should continue to reflect the committed state (match HEAD).
        # This is how Lit works - index represents staged area.
        
    except Exception as e:
        click.echo(error(f"Failed to create commit: {e}"))
        raise click.Abort()
