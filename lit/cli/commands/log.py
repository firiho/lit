"""Log command - show commit history."""

import click
from pathlib import Path
from datetime import datetime
from collections import defaultdict
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


def get_all_refs(repo):
    """
    Get all refs (branches, tags) with their commit hashes.
    
    Returns dict mapping commit_hash -> list of ref names
    """
    refs = defaultdict(list)
    
    # Local branches
    heads_dir = repo.lit_dir / 'refs' / 'heads'
    if heads_dir.exists():
        for branch_file in heads_dir.iterdir():
            if branch_file.is_file():
                commit_hash = branch_file.read_text().strip()
                refs[commit_hash].append(f"refs/heads/{branch_file.name}")
    
    # Remote tracking branches
    remotes_dir = repo.lit_dir / 'refs' / 'remotes'
    if remotes_dir.exists():
        for remote_dir in remotes_dir.iterdir():
            if remote_dir.is_dir():
                for branch_file in remote_dir.iterdir():
                    if branch_file.is_file():
                        commit_hash = branch_file.read_text().strip()
                        refs[commit_hash].append(f"refs/remotes/{remote_dir.name}/{branch_file.name}")
    
    # Tags
    tags_dir = repo.lit_dir / 'refs' / 'tags'
    if tags_dir.exists():
        for tag_file in tags_dir.iterdir():
            if tag_file.is_file():
                commit_hash = tag_file.read_text().strip()
                refs[commit_hash].append(f"refs/tags/{tag_file.name}")
    
    return refs


def get_all_branch_tips(repo):
    """Get commit hashes from all branches (local + remote)."""
    tips = set()
    
    # Local branches
    heads_dir = repo.lit_dir / 'refs' / 'heads'
    if heads_dir.exists():
        for branch_file in heads_dir.iterdir():
            if branch_file.is_file():
                tips.add(branch_file.read_text().strip())
    
    # Remote tracking branches
    remotes_dir = repo.lit_dir / 'refs' / 'remotes'
    if remotes_dir.exists():
        for remote_dir in remotes_dir.iterdir():
            if remote_dir.is_dir():
                for branch_file in remote_dir.iterdir():
                    if branch_file.is_file():
                        tips.add(branch_file.read_text().strip())
    
    return list(tips)


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


def get_all_commits_history(repo, start_hashes, max_count=None):
    """
    Walk commit history from multiple starting points (all branches).
    
    Returns list of (commit_hash, commit) tuples sorted by timestamp (newest first).
    """
    all_commits = {}  # hash -> commit
    visited = set()
    queue = list(start_hashes)
    
    while queue:
        commit_hash = queue.pop(0)
        
        if commit_hash in visited:
            continue
        
        visited.add(commit_hash)
        
        try:
            commit = repo.read_object(commit_hash)
            if not isinstance(commit, Commit):
                continue
            
            all_commits[commit_hash] = commit
            
            # Add parents to queue
            for parent_hash in commit.parents:
                if parent_hash not in visited:
                    queue.append(parent_hash)
        except:
            continue
    
    # Sort by timestamp (newest first)
    history = [(h, c) for h, c in all_commits.items()]
    history.sort(key=lambda x: x[1].author_time, reverse=True)
    
    if max_count:
        history = history[:max_count]
    
    return history


def build_branch_graph(repo, history, refs_map):
    """
    Build ASCII graph showing branch structure.
    
    This creates a visual representation similar to `git log --graph --all`.
    
    Returns list of (graph_line, commit_hash, commit, decorations) tuples.
    """
    if not history:
        return []
    
    result = []
    
    # Build parent -> children map to detect fork points
    children_map = defaultdict(list)
    commit_set = set(h for h, c in history)
    for commit_hash, commit in history:
        for parent in commit.parents:
            children_map[parent].append(commit_hash)
    
    # Track active branches (columns in the graph)
    # Each entry is the commit hash we're tracking in that column
    active_branches = []  
    commit_to_column = {}  # Map commit hash to its column
    
    for i, (commit_hash, commit) in enumerate(history):
        # Build decorations (branch names, tags)
        decorations = []
        if commit_hash in refs_map:
            for ref in refs_map[commit_hash]:
                if ref.startswith('refs/heads/'):
                    decorations.append((ref[11:], 'branch'))
                elif ref.startswith('refs/remotes/'):
                    decorations.append((ref[13:], 'remote'))
                elif ref.startswith('refs/tags/'):
                    decorations.append((ref[10:], 'tag'))
        
        # Find which column this commit should be in
        col = commit_to_column.get(commit_hash)
        
        if col is None:
            # No column assigned yet - find a free one
            if None in active_branches:
                col = active_branches.index(None)
                active_branches[col] = commit_hash
            else:
                col = len(active_branches)
                active_branches.append(commit_hash)
            commit_to_column[commit_hash] = col
        
        # Build graph line - show the current state
        graph_parts = []
        is_merge = len(commit.parents) > 1
        
        for c in range(len(active_branches)):
            if c == col:
                graph_parts.append('*')
            elif active_branches[c] is not None:
                graph_parts.append('│')
            else:
                graph_parts.append(' ')
        
        # For merge commits, show the merge line
        if is_merge and len(commit.parents) > 1:
            # Find columns of second parent
            second_parent = commit.parents[1]
            if second_parent in commit_to_column:
                merge_col = commit_to_column[second_parent]
                if merge_col < len(graph_parts) and merge_col != col:
                    # Add merge indicator between columns
                    pass  # The column already shows the merge parent
        
        # Find all columns that have this commit as their target and merge them
        cols_merging = [c for c in range(len(active_branches)) if active_branches[c] == commit_hash]
        if len(cols_merging) > 1:
            for c in cols_merging[1:]:
                active_branches[c] = None
        
        # Update active branches for parents
        if commit.parents:
            # First parent continues in same column
            first_parent = commit.parents[0]
            active_branches[col] = first_parent
            
            if first_parent not in commit_to_column:
                commit_to_column[first_parent] = col
            
            # Additional parents get new columns (for merge commits)
            for parent in commit.parents[1:]:
                if parent not in commit_to_column:
                    if None in active_branches:
                        new_col = active_branches.index(None)
                        active_branches[new_col] = parent
                    else:
                        new_col = len(active_branches)
                        active_branches.append(parent)
                    commit_to_column[parent] = new_col
        else:
            # No parents - this is a root commit, close the column
            active_branches[col] = None
        
        # Clean up empty trailing columns
        while active_branches and active_branches[-1] is None:
            active_branches.pop()
        
        graph_line = ' '.join(graph_parts) + ' '
        result.append((graph_line, commit_hash, commit, decorations))
    
    return result


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


def display_commit_oneline(graph, commit_hash, commit, decorations=None):
    """Display commit in one-line format."""
    short_hash = f"{Fore.YELLOW}{commit_hash[:7]}{Style.RESET_ALL}"
    
    # Build decorations string
    deco_str = ""
    if decorations:
        deco_parts = []
        for name, deco_type in decorations:
            if deco_type == 'branch':
                deco_parts.append(f"{Fore.GREEN}{name}{Style.RESET_ALL}")
            elif deco_type == 'remote':
                deco_parts.append(f"{Fore.RED}{name}{Style.RESET_ALL}")
            elif deco_type == 'tag':
                deco_parts.append(f"{Fore.YELLOW}tag: {name}{Style.RESET_ALL}")
        if deco_parts:
            deco_str = f" {Fore.YELLOW}({Style.RESET_ALL}{', '.join(deco_parts)}{Fore.YELLOW}){Style.RESET_ALL}"
    
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
    
    click.echo(f"{Fore.GREEN}{graph}{Style.RESET_ALL}{short_hash}{deco_str} - {message} {Fore.CYAN}({date_short}){Style.RESET_ALL} {Fore.BLUE}<{author}>{Style.RESET_ALL}")


def display_commit_full(graph, commit_hash, commit, show_graph=True, decorations=None):
    """Display commit in full format."""
    # Build decorations string
    deco_str = ""
    if decorations:
        deco_parts = []
        for name, deco_type in decorations:
            if deco_type == 'branch':
                deco_parts.append(f"{Fore.GREEN}{name}{Style.RESET_ALL}")
            elif deco_type == 'remote':
                deco_parts.append(f"{Fore.RED}{name}{Style.RESET_ALL}")
            elif deco_type == 'tag':
                deco_parts.append(f"{Fore.YELLOW}tag: {name}{Style.RESET_ALL}")
        if deco_parts:
            deco_str = f" {Fore.YELLOW}({Style.RESET_ALL}{', '.join(deco_parts)}{Fore.YELLOW}){Style.RESET_ALL}"
    
    # Commit header with decorations
    merge_str = f" {Fore.CYAN}(merge){Style.RESET_ALL}" if len(commit.parents) > 1 else ""
    graph_str = f" {Fore.GREEN}{graph.strip()}{Style.RESET_ALL}" if show_graph and graph else ""
    
    click.echo(f"{Fore.YELLOW}commit {commit_hash}{Style.RESET_ALL}{deco_str}{merge_str}{graph_str}")
    
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
@click.option('--all', 'show_all', is_flag=True, help='Show commits from all branches')
@click.option('--decorate', is_flag=True, default=True, help='Show branch/tag names (default: True)')
@click.argument('commit', required=False)
def log_cmd(max_count, oneline, graph, no_graph, show_all, decorate, commit):
    """
    Show commit logs.
    
    Displays commit history starting from HEAD or specified commit.
    By default shows full commit information with ASCII graph.
    
    Examples:
        lit log                    # Show all commits from HEAD
        lit log -n 10              # Show last 10 commits
        lit log --oneline          # Show compact one-line format
        lit log --all              # Show commits from ALL branches
        lit log --all --oneline    # Compact view of entire repo graph
        lit log --no-graph         # Disable graph visualization
        lit log a1b2c3d            # Show history from specific commit
    """
    repo = Repository.find_repository()
    if not repo:
        click.echo(error("Not a lit repository"))
        raise click.Abort()
    
    # Get refs map for decorations
    refs_map = get_all_refs(repo) if decorate else {}
    
    # Determine starting points
    if show_all:
        # Get all branch tips
        start_hashes = get_all_branch_tips(repo)
        if not start_hashes:
            # Fall back to HEAD
            start_hash = get_current_commit(repo)
            start_hashes = [start_hash] if start_hash else []
    elif commit:
        # Try to resolve short hash
        start_hash = find_commit_by_prefix(repo, commit)
        if not start_hash:
            click.echo(error(f"Commit not found: {commit}"))
            raise click.Abort()
        start_hashes = [start_hash]
    else:
        start_hash = get_current_commit(repo)
        start_hashes = [start_hash] if start_hash else []
    
    if not start_hashes:
        click.echo(warning("No commits yet"))
        return
    
    # Validate at least one commit exists
    try:
        test_commit = repo.read_object(start_hashes[0])
        if not isinstance(test_commit, Commit):
            click.echo(error(f"Not a valid commit: {start_hashes[0]}"))
            raise click.Abort()
    except:
        click.echo(error(f"Commit not found: {start_hashes[0]}"))
        raise click.Abort()
    
    # Get commit history
    if show_all:
        history = get_all_commits_history(repo, start_hashes, max_count)
    else:
        history = get_commit_history(repo, start_hashes[0], max_count)
    
    if not history:
        click.echo(warning("No commits to display"))
        return
    
    # Determine if we should show graph
    show_graph_output = graph and not no_graph
    
    # Build graph structure
    if show_all and show_graph_output:
        # Use branch graph for --all
        commit_graph = build_branch_graph(repo, history, refs_map)
    elif show_graph_output or oneline:
        # Simple graph for single branch
        simple_graph = build_commit_graph(history)
        # Add empty decorations for compatibility
        commit_graph = [(g, h, c, refs_map.get(h, [])) for g, h, c in simple_graph]
        # Convert refs to decoration format
        commit_graph = [
            (g, h, c, [(ref.split('/')[-1], 'branch' if 'heads' in ref else 'remote' if 'remotes' in ref else 'tag') for ref in refs_map.get(h, [])])
            for g, h, c in simple_graph
        ]
    else:
        commit_graph = [(None, h, c, []) for h, c in history]
    
    # Display commits
    for item in commit_graph:
        if len(item) == 4:
            graph_line, commit_hash, commit_obj, decorations = item
        else:
            graph_line, commit_hash, commit_obj = item
            decorations = []
        
        if oneline:
            display_commit_oneline(graph_line or "* ", commit_hash, commit_obj, decorations)
        else:
            display_commit_full(graph_line, commit_hash, commit_obj, show_graph_output, decorations)
