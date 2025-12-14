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
    Build ASCII graph showing branch structure similar to lit log --graph.
    
    Produces output like:
    *   commit (merge)
    |\  
    | * commit on branch
    * | commit on main
    |/  
    * common ancestor
    
    Returns list of (graph_line, commit_hash, commit, decorations) tuples.
    """
    if not history:
        return []
    
    result = []
    
    # Colors for different columns
    COLORS = [
        Fore.RED,
        Fore.GREEN, 
        Fore.YELLOW,
        Fore.BLUE,
        Fore.MAGENTA,
        Fore.CYAN,
    ]
    
    # Each column tracks the commit hash it's "expecting" to see
    columns = []
    
    for i, (commit_hash, commit) in enumerate(history):
        # Build decorations
        decorations = []
        if commit_hash in refs_map:
            for ref in refs_map[commit_hash]:
                if ref.startswith('refs/heads/'):
                    decorations.append((ref[11:], 'branch'))
                elif ref.startswith('refs/remotes/'):
                    decorations.append((ref[13:], 'remote'))
                elif ref.startswith('refs/tags/'):
                    decorations.append((ref[10:], 'tag'))
        
        # Find column(s) expecting this commit
        my_cols = [c for c, h in enumerate(columns) if h == commit_hash]
        
        if not my_cols:
            # New branch starting - find slot
            if None in columns:
                col = columns.index(None)
            else:
                col = len(columns)
                columns.append(None)
            columns[col] = commit_hash
            my_cols = [col]
        
        col = my_cols[0]
        is_merge = len(commit.parents) > 1
        
        # === COMMIT LINE ===
        commit_line = _render_line(columns, col, '*', COLORS)
        result.append((commit_line, commit_hash, commit, decorations))
        
        # Update columns: clear this commit
        for c in my_cols:
            columns[c] = None
        
        # Figure out where parents go
        parent_positions = []
        if commit.parents:
            # First parent stays in same column
            columns[col] = commit.parents[0]
            parent_positions.append(col)
            
            # Additional parents (merge)
            for parent in commit.parents[1:]:
                # Already tracked?
                existing = [c for c, h in enumerate(columns) if h == parent]
                if existing:
                    parent_positions.append(existing[0])
                else:
                    # New column to the right
                    new_col = col + 1
                    while new_col < len(columns) and columns[new_col] is not None:
                        new_col += 1
                    if new_col >= len(columns):
                        columns.append(parent)
                    else:
                        columns[new_col] = parent
                    parent_positions.append(new_col if new_col < len(columns) else len(columns) - 1)
        
        # === CONNECTOR LINE FOR MERGES ===
        if is_merge and len(parent_positions) > 1:
            # Draw |\  line
            connector = _render_merge_connector(columns, col, parent_positions, COLORS)
            result.append((connector, None, None, None))
        
        # === CONVERGENCE LINE (when branches join back) ===
        # Check if any columns to the right will merge into primary
        merge_cols = [c for c in range(col + 1, len(columns)) 
                      if columns[c] is not None and columns[c] == columns[col]]
        if merge_cols:
            for mc in merge_cols:
                columns[mc] = None
            conv_line = _render_convergence(columns, col, merge_cols, COLORS)
            result.append((conv_line, None, None, None))
        
        # Trim trailing empty columns
        while columns and columns[-1] is None:
            columns.pop()
    
    return result


def _render_line(columns, star_col, char, colors):
    """
    Render a commit line. Each column is 2 chars wide.
    Example: "* | " for star in col 0, pipe in col 1
    """
    parts = []
    for c in range(len(columns)):
        color = colors[c % len(colors)]
        if c == star_col:
            parts.append(f"{color}{char}{Style.RESET_ALL} ")
        elif columns[c] is not None:
            parts.append(f"{color}|{Style.RESET_ALL} ")
        else:
            parts.append("  ")
    return ''.join(parts)


def _render_merge_connector(columns, primary, parent_cols, colors):
    """
    Render merge connector: |\  
    The backslash connects primary column to the branch column.
    """
    parts = []
    max_col = max(max(parent_cols), len(columns) - 1) if parent_cols else len(columns) - 1
    
    for c in range(max_col + 1):
        color = colors[c % len(colors)]
        
        if c == primary:
            # Primary column: | followed by \ pointing to branch
            parts.append(f"{color}|{Style.RESET_ALL}")
            parts.append(f"{colors[(primary + 1) % len(colors)]}\\{Style.RESET_ALL}")
        elif c > primary and c in parent_cols:
            # The branch column after the connector - just space
            parts.append("  ")
        elif c < len(columns) and columns[c] is not None:
            parts.append(f"{color}|{Style.RESET_ALL} ")
        else:
            parts.append("  ")
    
    return ''.join(parts)


def _render_convergence(columns, target, merging_cols, colors):
    """
    Render convergence: |/  
    The slash shows a branch merging back.
    """
    parts = []
    
    for c in range(len(columns)):
        color = colors[c % len(colors)]
        
        if c == target:
            # Target column: | followed by / from the merging branch
            parts.append(f"{color}|{Style.RESET_ALL}")
            if merging_cols and min(merging_cols) == c + 1:
                parts.append(f"{colors[(c + 1) % len(colors)]}/{Style.RESET_ALL}")
            else:
                parts.append(" ")
        elif c in merging_cols:
            # Merging column - already shown as /
            parts.append("  ")
        elif columns[c] is not None:
            parts.append(f"{color}|{Style.RESET_ALL} ")
        else:
            parts.append("  ")
    
    return ''.join(parts)


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
@click.option('--graph', is_flag=True, help='Show ASCII graph of branch structure')
@click.option('--all', 'show_all', is_flag=True, help='Show commits from all branches')
@click.option('--decorate', is_flag=True, default=True, help='Show branch/tag names (default: True)')
@click.argument('commit', required=False)
def log_cmd(max_count, oneline, graph, show_all, decorate, commit):
    """
    Show commit logs.
    
    Displays commit history starting from HEAD or specified commit.
    
    Examples:
        lit log                    # Show all commits from HEAD
        lit log -n 10              # Show last 10 commits
        lit log --oneline          # Show compact one-line format
        lit log --graph            # Show ASCII graph of branches
        lit log --all              # Show commits from ALL branches
        lit log --graph --all --oneline  # Lit-style graph view
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
    
    # Build graph structure based on options
    if graph:
        # Use proper branch graph with merge lines
        commit_graph = build_branch_graph(repo, history, refs_map)
    elif oneline:
        # Simple graph for oneline without --graph
        simple_graph = build_commit_graph(history)
        commit_graph = [
            (g, h, c, [(ref.split('/')[-1], 'branch' if 'heads' in ref else 'remote' if 'remotes' in ref else 'tag') for ref in refs_map.get(h, [])])
            for g, h, c in simple_graph
        ]
    else:
        # No graph, just list commits
        commit_graph = [
            (None, h, c, [(ref.split('/')[-1], 'branch' if 'heads' in ref else 'remote' if 'remotes' in ref else 'tag') for ref in refs_map.get(h, [])])
            for h, c in history
        ]
    
    # Display commits
    for item in commit_graph:
        if len(item) == 4:
            graph_line, commit_hash, commit_obj, decorations = item
        else:
            graph_line, commit_hash, commit_obj = item
            decorations = []
        
        # Skip connector lines in non-graph mode, or just print them in graph mode
        if commit_hash is None:
            if graph:
                click.echo(graph_line)
            continue
        
        if oneline:
            display_commit_oneline(graph_line or "* ", commit_hash, commit_obj, decorations)
        else:
            display_commit_full(graph_line, commit_hash, commit_obj, graph, decorations)
