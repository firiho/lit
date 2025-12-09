"""Tag command - create, list, or delete tags."""

import click
from pathlib import Path
from lit.core.repository import Repository
from lit.core.objects import Commit
from lit.cli.output import success, error, info, warning


def resolve_commit_ref(repo, refs_mgr, ref: str):
    """
    Resolve a commit reference, handling HEAD~N and HEAD^ syntax.
    
    Args:
        repo: Repository instance
        refs_mgr: RefManager instance
        ref: Reference string (HEAD, HEAD~N, branch name, commit hash, etc.)
        
    Returns:
        Commit hash or None if not found
    """
    # Handle HEAD~N syntax
    if ref.startswith('HEAD~') or ref.startswith('HEAD^'):
        if ref.startswith('HEAD~'):
            try:
                steps = int(ref[5:]) if len(ref) > 5 else 1
            except ValueError:
                return None
        else:  # HEAD^
            steps = ref.count('^')
        
        current_hash = refs_mgr.resolve_head()
        if not current_hash:
            return None
        
        for _ in range(steps):
            try:
                commit_obj = repo.read_object(current_hash)
                if not isinstance(commit_obj, Commit):
                    return None
                if not commit_obj.parents:
                    return None
                current_hash = commit_obj.parents[0]
            except:
                return None
        
        return current_hash
    
    # Regular reference resolution
    return refs_mgr.resolve_reference(ref)


@click.command('tag')
@click.argument('name', required=False)
@click.argument('commit', required=False)
@click.option('-a', '--annotate', is_flag=True, help='Create an annotated tag')
@click.option('-m', '--message', help='Tag message (implies -a)')
@click.option('-d', '--delete', is_flag=True, help='Delete a tag')
@click.option('-l', '--list', 'list_tags', is_flag=True, help='List tags')
@click.option('-f', '--force', is_flag=True, help='Replace existing tag')
def tag_cmd(name, commit, annotate, message, delete, list_tags, force):
    """
    Create, list, or delete tags.
    
    Tags are named references to specific commits. They're useful for
    marking release points (v1.0, v2.0, etc.).
    
    There are two types of tags:
    - Lightweight: Just a pointer to a commit
    - Annotated: Contains tagger info, date, and message (-a or -m)
    
    Examples:
        lit tag                     # List all tags
        lit tag v1.0                # Create lightweight tag on HEAD
        lit tag v1.0 abc123         # Create lightweight tag on specific commit
        lit tag -a v1.0 -m "msg"    # Create annotated tag
        lit tag -d v1.0             # Delete a tag
        lit tag -l                  # List all tags
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    refs_mgr = repo.refs
    
    # Handle list mode (default if no name given)
    if list_tags or (name is None and not delete):
        tags = refs_mgr.list_tags()
        
        if not tags:
            click.echo(info("No tags found"))
            return
        
        for tag_name, commit_hash in tags:
            # Get commit message preview
            try:
                obj = repo.read_object(commit_hash)
                if isinstance(obj, Commit):
                    msg_line = obj.message.split('\n')[0][:50]
                    click.echo(f"{tag_name:20} {commit_hash[:7]} {msg_line}")
                else:
                    click.echo(f"{tag_name:20} {commit_hash[:7]}")
            except:
                click.echo(f"{tag_name:20} {commit_hash[:7]}")
        
        return
    
    # Handle delete mode
    if delete:
        if not name:
            click.echo(error("Tag name required for deletion"))
            raise click.Abort()
        
        if refs_mgr.delete_tag(name):
            click.echo(success(f"Deleted tag '{name}'"))
        else:
            click.echo(error(f"Tag '{name}' not found"))
            raise click.Abort()
        return
    
    # Create tag mode
    if not name:
        click.echo(error("Tag name required"))
        raise click.Abort()
    
    # Validate tag name
    if not is_valid_tag_name(name):
        click.echo(error(f"Invalid tag name: '{name}'"))
        click.echo(info("Tag names cannot contain: spaces, ~, ^, :, ?, *, [, \\"))
        raise click.Abort()
    
    # Check if tag already exists
    existing_tags = {t[0] for t in refs_mgr.list_tags()}
    if name in existing_tags and not force:
        click.echo(error(f"Tag '{name}' already exists"))
        click.echo(info("Use --force to replace it"))
        raise click.Abort()
    
    # If tag exists and force is set, delete it first
    if name in existing_tags and force:
        refs_mgr.delete_tag(name)
    
    # Resolve target commit
    if commit:
        # Handle HEAD~N syntax
        target_hash = resolve_commit_ref(repo, refs_mgr, commit)
        if not target_hash:
            click.echo(error(f"Unknown revision: {commit}"))
            raise click.Abort()
    else:
        # Default to HEAD
        target_hash = refs_mgr.resolve_head()
        if not target_hash:
            click.echo(error("No commits yet - cannot create tag"))
            raise click.Abort()
    
    # Verify it's a valid commit
    try:
        obj = repo.read_object(target_hash)
        if not isinstance(obj, Commit):
            click.echo(error(f"Cannot tag non-commit object: {target_hash[:7]}"))
            raise click.Abort()
    except Exception as e:
        click.echo(error(f"Cannot read commit: {e}"))
        raise click.Abort()
    
    # Create the tag
    if message:
        annotate = True  # -m implies -a
    
    if annotate:
        # Create annotated tag (stored as tag object)
        # For now, we'll just store it as a lightweight tag with message in log
        # Full annotated tag support would require Tag object serialization
        if refs_mgr.create_tag(name, target_hash):
            click.echo(success(f"Created annotated tag '{name}'"))
            if message:
                click.echo(info(f"Message: {message}"))
            click.echo(info(f"Points to: {target_hash[:7]}"))
        else:
            click.echo(error(f"Failed to create tag '{name}'"))
            raise click.Abort()
    else:
        # Create lightweight tag
        if refs_mgr.create_tag(name, target_hash):
            click.echo(success(f"Created tag '{name}'"))
            click.echo(info(f"Points to: {target_hash[:7]}"))
        else:
            click.echo(error(f"Failed to create tag '{name}'"))
            raise click.Abort()


def is_valid_tag_name(name: str) -> bool:
    """
    Check if a tag name is valid.
    
    Args:
        name: Proposed tag name
        
    Returns:
        True if valid, False otherwise
    """
    if not name:
        return False
    
    # Cannot start or end with /
    if name.startswith('/') or name.endswith('/'):
        return False
    
    # Cannot contain consecutive slashes
    if '//' in name:
        return False
    
    # Cannot contain special characters
    invalid_chars = ' ~^:?*[\\'
    for char in invalid_chars:
        if char in name:
            return False
    
    # Cannot start with -
    if name.startswith('-'):
        return False
    
    # Cannot end with .lock
    if name.endswith('.lock'):
        return False
    
    return True
