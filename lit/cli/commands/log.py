"""Log command - show commit history."""

import click
from pathlib import Path
from datetime import datetime
from lit.core.repository import Repository
from lit.core.objects import Commit
from lit.cli.output import success, error, info, warning
from colorama import Fore, Style


def format_timestamp(timestamp):
    """Format Unix timestamp to readable date."""
    try:
        dt = datetime.fromtimestamp(int(timestamp))
        return dt.strftime("%a %b %d %H:%M:%S %Y")
    except:
        return "Unknown date"


def get_commit_history(repo, start_hash, max_count=None):
    """
    Walk commit history from starting commit.
    
    Returns list of (commit_hash, commit) tuples in reverse chronological order.
    """
    history = []
    visited = set()
    queue = [start_hash]
    
    while queue and (max_count is None or len(history) < max_count):
        commit_hash = queue.pop(0)
        
        if commit_hash in visited:
            continue
        
        visited.add(commit_hash)
        
        try:
            commit = repo.read_object(commit_hash)
            if not isinstance(commit, Commit):
                continue
            
            history.append((commit_hash, commit))
            
            # Add parents to queue
            for parent_hash in commit.parents:
                if parent_hash not in visited:
                    queue.append(parent_hash)
        except:
            continue
    
    return history


def build_commit_graph(history):
    """
    Build ASCII graph structure for commits.
    
    Returns list of (graph_line, commit_hash, commit) tuples.
    """
    if not history:
        return []
    
    # Build graph with visual connectors
    result = []
    
    for i, (commit_hash, commit) in enumerate(history):
        # Determine if this is a merge commit
        is_merge = len(commit.parents) > 1
        is_first = i == 0
        is_last = i == len(history) - 1
        
        if is_first:
            # First commit (most recent)
            if is_merge:
                graph = "* "  # Merge point
            else:
                graph = "* "  # Regular commit
        elif is_last:
            # Last commit (oldest shown)
            graph = "* "
        else:
            # Middle commits
            if is_merge:
                graph = "* "  # Merge commit
            else:
                graph = "* "  # Regular commit
        
        result.append((graph, commit_hash, commit))
    
    return result


def display_commit_oneline(graph, commit_hash, commit):
    """Display commit in one-line format."""
    short_hash = f"{Fore.YELLOW}{commit_hash[:7]}{Style.RESET_ALL}"
    
    # Get first line of message
    message = commit.message.split('\n')[0]
    if len(message) > 60:
        message = message[:57] + "..."
    
    # Format date (relative or short format)
    date_str = format_timestamp(commit.author_time).split()[1:4]  # "Oct 31 16:33:00"
    date_short = f"{date_str[0]} {date_str[1]}"  # "Oct 31"
    
    # Extract author name (without email)
    author = commit.author
    if '<' in author:
        author = author.split('<')[0].strip()
    if len(author) > 15:
        author = author[:12] + "..."
    
    click.echo(f"{Fore.GREEN}{graph}{Style.RESET_ALL}{short_hash} - {message} {Fore.CYAN}({date_short}){Style.RESET_ALL} {Fore.BLUE}<{author}>{Style.RESET_ALL}")


def display_commit_full(graph, commit_hash, commit, show_graph=True):
    """Display commit in full format."""
    # Commit header with decorations
    if show_graph:
        if len(commit.parents) > 1:
            # Merge commit - highlight it
            click.echo(f"{Fore.YELLOW}commit {commit_hash}{Style.RESET_ALL} {Fore.CYAN}(merge){Style.RESET_ALL} {Fore.GREEN}{graph.strip()}{Style.RESET_ALL}")
        else:
            click.echo(f"{Fore.YELLOW}commit {commit_hash}{Style.RESET_ALL} {Fore.GREEN}{graph.strip()}{Style.RESET_ALL}")
    else:
        if len(commit.parents) > 1:
            click.echo(f"{Fore.YELLOW}commit {commit_hash}{Style.RESET_ALL} {Fore.CYAN}(merge){Style.RESET_ALL}")
        else:
            click.echo(f"{Fore.YELLOW}commit {commit_hash}{Style.RESET_ALL}")
    
    # Parents
    if commit.parents:
        if len(commit.parents) == 1:
            click.echo(f"Parent:    {commit.parents[0]}")
        else:
            click.echo(f"Merge:     {' '.join(p for p in commit.parents)}")
    
    # Author
    click.echo(f"Author:    {commit.author}")
    
    # Committer (if different from author)
    if commit.committer and commit.committer != commit.author:
        click.echo(f"Committer: {commit.committer}")
    
    # Date
    date_str = format_timestamp(commit.author_time)
    click.echo(f"Date:      {date_str}")
    
    # Message
    click.echo()
    for line in commit.message.split('\n'):
        click.echo(f"    {line}")
    click.echo()


def get_current_commit(repo):
    """Get current HEAD commit hash."""
    head_file = repo.head_file
    
    if not head_file.exists():
        return None
    
    head_content = head_file.read_text().strip()
    
    if head_content.startswith('ref: '):
        ref_path = head_content[5:]
        ref_file = repo.lit_dir / ref_path
        
        if not ref_file.exists():
            return None
        
        return ref_file.read_text().strip()
    else:
        return head_content


def find_commit_by_prefix(repo, prefix):
    """Find commit by hash prefix."""
    if len(prefix) == 40:
        # Full hash provided
        return prefix
    
    # Search in objects directory
    objects_dir = repo.objects_dir
    matches = []
    
    # The first 2 characters are the directory name
    if len(prefix) >= 2:
        subdir = objects_dir / prefix[:2]
        if subdir.exists():
            for obj_file in subdir.iterdir():
                full_hash = prefix[:2] + obj_file.name
                if full_hash.startswith(prefix):
                    matches.append(full_hash)
    else:
        # Search all subdirectories
        for subdir in objects_dir.iterdir():
            if subdir.is_dir() and len(subdir.name) == 2:
                for obj_file in subdir.iterdir():
                    full_hash = subdir.name + obj_file.name
                    if full_hash.startswith(prefix):
                        matches.append(full_hash)
    
    if len(matches) == 0:
        return None
    elif len(matches) == 1:
        return matches[0]
    else:
        # Ambiguous - return None or raise error
        return None


@click.command('log')
@click.option('-n', '--max-count', type=int, help='Limit number of commits to show')
@click.option('--oneline', is_flag=True, help='Show commits in one-line format')
@click.option('--graph', is_flag=True, default=True, help='Show ASCII graph (default: True)')
@click.option('--no-graph', is_flag=True, help='Disable ASCII graph')
@click.argument('commit', required=False)
def log_cmd(max_count, oneline, graph, no_graph, commit):
    """
    Show commit logs.
    
    Displays commit history starting from HEAD or specified commit.
    By default shows full commit information with ASCII graph.
    
    Examples:
        lit log                    # Show all commits from HEAD
        lit log -n 10              # Show last 10 commits
        lit log --oneline          # Show compact one-line format
        lit log --no-graph         # Disable graph visualization
        lit log a1b2c3d            # Show history from specific commit
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    # Get starting commit
    if commit:
        # Try to resolve short hash
        start_hash = find_commit_by_prefix(repo, commit)
        if not start_hash:
            click.echo(error(f"Commit not found: {commit}"))
            raise click.Abort()
    else:
        start_hash = get_current_commit(repo)
    
    if not start_hash:
        click.echo(warning("No commits yet"))
        return
    
    # Validate commit exists
    try:
        test_commit = repo.read_object(start_hash)
        if not isinstance(test_commit, Commit):
            click.echo(error(f"Not a valid commit: {start_hash}"))
            raise click.Abort()
    except:
        click.echo(error(f"Commit not found: {start_hash}"))
        raise click.Abort()
    
    # Get commit history
    history = get_commit_history(repo, start_hash, max_count)
    
    if not history:
        click.echo(warning("No commits to display"))
        return
    
    # Determine if we should show graph
    show_graph = graph and not no_graph and not oneline
    
    # Build graph structure
    if show_graph or oneline:
        commit_graph = build_commit_graph(history)
    else:
        commit_graph = [(None, h, c) for h, c in history]
    
    # Display commits
    for graph_line, commit_hash, commit_obj in commit_graph:
        if oneline:
            display_commit_oneline(graph_line, commit_hash, commit_obj)
        else:
            display_commit_full(graph_line, commit_hash, commit_obj, show_graph)
