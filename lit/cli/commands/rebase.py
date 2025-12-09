"""Rebase command for Lit VCS."""

import click
import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Tuple
from colorama import Fore, Style

from lit.core.repository import Repository
from lit.core.objects import Commit, Blob, Tree
from lit.core.index import Index
from lit.operations.merge import MergeEngine, MergeConflict
from lit.cli.output import error, success, info, warning
from lit.cli.commands.cherry_pick import (
    get_commit_changes, 
    get_tree_files_recursive, 
    resolve_commit_ref
)


@dataclass
class RebaseState:
    """State of an in-progress rebase."""
    onto: str                    # Commit to rebase onto
    head_name: str               # Original branch name
    orig_head: str               # Original HEAD before rebase
    commits: List[str]           # Commits to replay (oldest first)
    current_index: int           # Current commit being applied
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RebaseState':
        return cls(**data)


def get_rebase_dir(repo) -> Path:
    """Get the rebase state directory."""
    return repo.lit_dir / 'rebase-apply'


def is_rebase_in_progress(repo) -> bool:
    """Check if a rebase is in progress."""
    return get_rebase_dir(repo).exists()


def save_rebase_state(repo, state: RebaseState) -> None:
    """Save rebase state to disk."""
    rebase_dir = get_rebase_dir(repo)
    rebase_dir.mkdir(parents=True, exist_ok=True)
    
    state_file = rebase_dir / 'state.json'
    state_file.write_text(json.dumps(state.to_dict(), indent=2))


def load_rebase_state(repo) -> Optional[RebaseState]:
    """Load rebase state from disk."""
    state_file = get_rebase_dir(repo) / 'state.json'
    if not state_file.exists():
        return None
    
    try:
        data = json.loads(state_file.read_text())
        return RebaseState.from_dict(data)
    except (json.JSONDecodeError, KeyError):
        return None


def clear_rebase_state(repo) -> None:
    """Clear rebase state files."""
    import shutil
    rebase_dir = get_rebase_dir(repo)
    if rebase_dir.exists():
        shutil.rmtree(rebase_dir)


def get_commits_to_replay(repo, onto: str, head: str) -> List[str]:
    """
    Get commits that need to be replayed during rebase.
    
    Returns commits from 'onto' to 'head' (exclusive of onto, inclusive of head),
    in order from oldest to newest.
    """
    # Get ancestors of onto
    onto_ancestors = set()
    to_visit = [onto]
    while to_visit:
        current = to_visit.pop(0)
        if current in onto_ancestors:
            continue
        onto_ancestors.add(current)
        commit = repo.read_object(current)
        if isinstance(commit, Commit):
            to_visit.extend(commit.parents)
    
    # Get commits from head that are not in onto's ancestry
    commits = []
    to_visit = [head]
    visited = set()
    
    while to_visit:
        current = to_visit.pop(0)
        if current in visited or current in onto_ancestors:
            continue
        visited.add(current)
        commits.append(current)
        
        commit = repo.read_object(current)
        if isinstance(commit, Commit):
            to_visit.extend(commit.parents)
    
    # Reverse to get oldest first
    commits.reverse()
    return commits


def apply_commit_three_way(repo, commit_hash: str, message: str = None) -> Tuple[Optional[str], List[MergeConflict]]:
    """
    Apply a commit's changes to the current HEAD using three-way merge.
    
    For rebase, when applying a commit C (with parent P) onto HEAD:
    - Base: P (parent of the commit being applied)
    - Ours: HEAD (current state we're rebasing onto)
    - Theirs: C (the commit being applied)
    
    This properly detects when both branches modify the same lines.
    
    Returns:
        (new_commit_hash, conflicts) - new_commit_hash is None if conflicts
    """
    commit = repo.read_object(commit_hash)
    if not isinstance(commit, Commit):
        return None, [MergeConflict("", None, None, None)]
    
    # Get the parent of the commit being applied (base for merge)
    if not commit.parents:
        # Initial commit - just copy all files
        return apply_initial_commit(repo, commit, message)
    
    parent_hash = commit.parents[0]
    head_hash = repo.refs.resolve_head()
    
    if not head_hash:
        return None, [MergeConflict("HEAD", None, None, None)]
    
    # Use MergeEngine for proper three-way merge
    merge_engine = MergeEngine(repo)
    
    # Get file trees for all three versions
    parent_commit = repo.read_object(parent_hash)
    head_commit = repo.read_object(head_hash)
    
    if not isinstance(parent_commit, Commit) or not isinstance(head_commit, Commit):
        return None, [MergeConflict("invalid", None, None, None)]
    
    # Get file dictionaries
    base_files = get_tree_files_recursive(repo, parent_commit.tree)  # Parent of commit being applied
    ours_files = get_tree_files_recursive(repo, head_commit.tree)    # Current HEAD
    theirs_files = get_tree_files_recursive(repo, commit.tree)       # Commit being applied
    
    # Perform three-way merge
    merged_files, conflicts = merge_files_three_way(repo, base_files, ours_files, theirs_files, merge_engine)
    
    if conflicts:
        # Write conflict markers to working tree
        write_conflicts_to_workdir(repo, conflicts, merge_engine)
        return None, conflicts
    
    # Apply merged files to working tree and index
    apply_merged_files(repo, merged_files)
    
    # Create new commit
    new_hash = create_rebase_commit(repo, commit, message)
    return new_hash, []


def apply_initial_commit(repo, commit: Commit, message: str = None) -> Tuple[Optional[str], List[MergeConflict]]:
    """Apply an initial commit (no parent) during rebase."""
    tree_files = get_tree_files_recursive(repo, commit.tree)
    index = Index()
    
    for path, blob_hash in tree_files.items():
        blob = repo.read_object(blob_hash)
        if blob:
            full_path = repo.work_tree / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_bytes(blob.data)
            
            stat = full_path.stat()
            index.add_entry(
                path=path,
                sha1=blob_hash,
                mode=stat.st_mode,
                size=stat.st_size,
                mtime=int(stat.st_mtime),
                ctime=int(stat.st_ctime)
            )
    
    index.write(str(repo.index_file))
    new_hash = create_rebase_commit(repo, commit, message)
    return new_hash, []


def merge_files_three_way(
    repo, 
    base_files: Dict[str, str], 
    ours_files: Dict[str, str], 
    theirs_files: Dict[str, str],
    merge_engine: MergeEngine
) -> Tuple[Dict[str, str], List[MergeConflict]]:
    """
    Merge file dictionaries using three-way merge logic.
    
    Returns:
        Tuple of (merged_files, conflicts)
    """
    merged_files = {}
    conflicts = []
    
    # Get all file paths across all three versions
    all_paths = set(base_files.keys()) | set(ours_files.keys()) | set(theirs_files.keys())
    
    for path in sorted(all_paths):
        base_hash = base_files.get(path)
        ours_hash = ours_files.get(path)
        theirs_hash = theirs_files.get(path)
        
        # Case 1: File unchanged in both branches (or same change)
        if ours_hash == theirs_hash:
            if ours_hash:
                merged_files[path] = ours_hash
            continue
        
        # Case 2: File only changed in our branch (HEAD)
        if base_hash == theirs_hash and ours_hash != base_hash:
            if ours_hash:
                merged_files[path] = ours_hash
            continue
        
        # Case 3: File only changed in their branch (commit being applied)
        if base_hash == ours_hash and theirs_hash != base_hash:
            if theirs_hash:
                merged_files[path] = theirs_hash
            continue
        
        # Case 4: File changed in both branches - potential conflict
        base_content = get_blob_content(repo, base_hash) if base_hash else None
        ours_content = get_blob_content(repo, ours_hash) if ours_hash else None
        theirs_content = get_blob_content(repo, theirs_hash) if theirs_hash else None
        
        # Try line-based auto-merge
        merged_content = try_auto_merge(base_content, ours_content, theirs_content)
        
        if merged_content is not None:
            # Auto-merge succeeded
            blob = Blob(merged_content)
            merged_hash = repo.write_object(blob)
            merged_files[path] = merged_hash
        else:
            # Conflict detected
            conflicts.append(MergeConflict(
                path=path,
                base_content=base_content,
                ours_content=ours_content,
                theirs_content=theirs_content
            ))
    
    return merged_files, conflicts


def get_blob_content(repo, blob_hash: str) -> Optional[bytes]:
    """Get content of a blob."""
    try:
        blob = repo.read_object(blob_hash)
        return blob.data if blob else None
    except:
        return None


def try_auto_merge(
    base_content: Optional[bytes],
    ours_content: Optional[bytes],
    theirs_content: Optional[bytes]
) -> Optional[bytes]:
    """
    Try to automatically merge content using line-based merge.
    
    Returns:
        Merged content if successful, None if conflicts detected
    """
    # If any content is None (file added/deleted), can't auto-merge
    if base_content is None or ours_content is None or theirs_content is None:
        return None
    
    try:
        # Split into lines
        base_lines = base_content.decode('utf-8', errors='replace').splitlines(keepends=True)
        ours_lines = ours_content.decode('utf-8', errors='replace').splitlines(keepends=True)
        theirs_lines = theirs_content.decode('utf-8', errors='replace').splitlines(keepends=True)
        
        # Simple line-based merge
        if len(base_lines) != len(ours_lines) or len(base_lines) != len(theirs_lines):
            # Different number of lines - try diff-based merge
            return try_diff_based_merge(base_lines, ours_lines, theirs_lines)
        
        merged_lines = []
        for i, base_line in enumerate(base_lines):
            ours_line = ours_lines[i]
            theirs_line = theirs_lines[i]
            
            if ours_line == theirs_line:
                merged_lines.append(ours_line)
            elif ours_line == base_line:
                # Only changed in theirs
                merged_lines.append(theirs_line)
            elif theirs_line == base_line:
                # Only changed in ours
                merged_lines.append(ours_line)
            else:
                # Both changed same line - conflict
                return None
        
        return ''.join(merged_lines).encode('utf-8')
    except:
        return None


def try_diff_based_merge(
    base_lines: List[str],
    ours_lines: List[str],
    theirs_lines: List[str]
) -> Optional[bytes]:
    """
    Try a more sophisticated diff-based merge for files with different line counts.
    
    Uses a simple approach: if changes are in disjoint regions, merge them.
    """
    # Find which lines changed in each branch
    ours_changes = set()
    theirs_changes = set()
    
    # Compare ours vs base
    max_len = max(len(base_lines), len(ours_lines))
    for i in range(max_len):
        base_line = base_lines[i] if i < len(base_lines) else None
        ours_line = ours_lines[i] if i < len(ours_lines) else None
        if base_line != ours_line:
            ours_changes.add(i)
    
    # Compare theirs vs base
    max_len = max(len(base_lines), len(theirs_lines))
    for i in range(max_len):
        base_line = base_lines[i] if i < len(base_lines) else None
        theirs_line = theirs_lines[i] if i < len(theirs_lines) else None
        if base_line != theirs_line:
            theirs_changes.add(i)
    
    # If changes overlap, we have a conflict
    if ours_changes & theirs_changes:
        return None
    
    # No overlap - but if line counts differ, hard to merge safely
    # For now, return None to trigger conflict markers
    if len(ours_lines) != len(base_lines) or len(theirs_lines) != len(base_lines):
        return None
    
    return None  # Conservative: return conflict


def write_conflicts_to_workdir(repo, conflicts: List[MergeConflict], merge_engine: MergeEngine) -> None:
    """Write conflict markers to working tree files."""
    for conflict in conflicts:
        file_path = repo.work_tree / conflict.path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        conflicted_content = merge_engine.generate_conflict_markers(
            conflict.path,
            conflict.ours_content,
            conflict.theirs_content,
            conflict.base_content
        )
        
        file_path.write_bytes(conflicted_content)


def apply_merged_files(repo, merged_files: Dict[str, str]) -> None:
    """Apply merged files to working tree and index."""
    index = Index()
    if repo.index_file.exists():
        index.read(str(repo.index_file))
    
    for path, blob_hash in merged_files.items():
        blob = repo.read_object(blob_hash)
        if blob:
            full_path = repo.work_tree / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_bytes(blob.data)
            
            stat = full_path.stat()
            index.add_entry(
                path=path,
                sha1=blob_hash,
                mode=stat.st_mode,
                size=stat.st_size,
                mtime=int(stat.st_mtime),
                ctime=int(stat.st_ctime)
            )
    
    index.write(str(repo.index_file))


def create_rebase_commit(repo, original_commit: Commit, message: str = None) -> str:
    """Create a new commit during rebase."""
    # Build tree from index
    index = Index()
    index.read(str(repo.index_file))
    
    root = {}
    for path, entry in index.entries.items():
        parts = path.split('/')
        current = root
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        filename = parts[-1]
        current[filename] = (entry.sha1, entry.mode)
    
    tree_hash = write_tree_recursive(repo, root)
    
    # Get HEAD as parent
    head = repo.refs.resolve_head()
    
    # Create commit
    new_commit = Commit()
    new_commit.tree = tree_hash
    new_commit.parents = [head] if head else []
    new_commit.author = original_commit.author
    new_commit.author_time = original_commit.author_time
    new_commit.author_timezone = original_commit.author_timezone
    new_commit.committer = original_commit.committer
    new_commit.committer_time = int(time.time())
    new_commit.committer_timezone = original_commit.committer_timezone
    new_commit.message = message if message else original_commit.message
    
    commit_hash = repo.write_object(new_commit)
    
    # Update HEAD
    update_head(repo, commit_hash)
    
    return commit_hash


def write_tree_recursive(repo, node: dict) -> str:
    """Recursively write tree objects."""
    tree = Tree()
    
    for name, value in sorted(node.items()):
        if isinstance(value, tuple):
            sha1, mode = value
            if mode & 0o111:
                mode_str = '100755'
            else:
                mode_str = '100644'
            tree.add_entry(mode_str, 'blob', sha1, name)
        else:
            subtree_hash = write_tree_recursive(repo, value)
            tree.add_entry('040000', 'tree', subtree_hash, name)
    
    return repo.write_object(tree)


def update_head(repo, commit_hash: str) -> None:
    """Update HEAD to point to a commit."""
    head_content = (repo.lit_dir / 'HEAD').read_text().strip()
    if head_content.startswith('ref: '):
        branch_ref = head_content[5:]
        ref_path = repo.lit_dir / branch_ref
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        ref_path.write_text(commit_hash)
    else:
        (repo.lit_dir / 'HEAD').write_text(commit_hash)


def reset_to_commit(repo, commit_hash: str) -> None:
    """Reset working directory and index to a commit."""
    commit = repo.read_object(commit_hash)
    if not isinstance(commit, Commit):
        return
    
    tree_files = get_tree_files_recursive(repo, commit.tree)
    index = Index()
    
    for path, blob_hash in tree_files.items():
        blob = repo.read_object(blob_hash)
        if blob:
            full_path = repo.work_tree / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_bytes(blob.data)
            
            stat = full_path.stat()
            index.add_entry(
                path=path,
                sha1=blob_hash,
                mode=stat.st_mode,
                size=stat.st_size,
                mtime=int(stat.st_mtime),
                ctime=int(stat.st_ctime)
            )
    
    index.write(str(repo.index_file))


@click.command('rebase')
@click.argument('upstream', required=False)
@click.option('--continue', 'continue_rebase', is_flag=True, help='Continue after resolving conflicts')
@click.option('--abort', 'abort_rebase', is_flag=True, help='Abort rebase and restore original branch')
@click.option('--skip', is_flag=True, help='Skip current commit and continue')
@click.option('-i', '--interactive', is_flag=True, help='Interactive rebase (not implemented)')
def rebase_cmd(upstream, continue_rebase, abort_rebase, skip, interactive):
    """Reapply commits on top of another base tip.
    
    Rebasing takes commits from your current branch that aren't in the
    upstream branch and replays them on top of the upstream branch.
    
    Examples:
        lit rebase main        Rebase current branch onto main
        lit rebase --continue  Continue after resolving conflicts
        lit rebase --abort     Cancel rebase and restore original state
        lit rebase --skip      Skip the current conflicting commit
    """
    try:
        repo = Repository.find_repository()
        if not repo:
            click.echo(error("Not a lit repository"))
            return
        
        # Handle --abort
        if abort_rebase:
            if not is_rebase_in_progress(repo):
                click.echo(error("No rebase in progress"))
                return
            
            state = load_rebase_state(repo)
            if state:
                # Restore original HEAD
                update_head(repo, state.orig_head)
                reset_to_commit(repo, state.orig_head)
            
            clear_rebase_state(repo)
            click.echo(success("Rebase aborted"))
            return
        
        # Handle --skip
        if skip:
            if not is_rebase_in_progress(repo):
                click.echo(error("No rebase in progress"))
                return
            
            state = load_rebase_state(repo)
            if not state:
                click.echo(error("Invalid rebase state"))
                clear_rebase_state(repo)
                return
            
            # Move to next commit
            state.current_index += 1
            
            if state.current_index >= len(state.commits):
                # Rebase complete
                clear_rebase_state(repo)
                click.echo(success("Rebase complete"))
                return
            
            # Save state and continue
            save_rebase_state(repo, state)
            
            # Apply remaining commits
            apply_remaining_commits(repo, state)
            return
        
        # Handle --continue
        if continue_rebase:
            if not is_rebase_in_progress(repo):
                click.echo(error("No rebase in progress"))
                return
            
            state = load_rebase_state(repo)
            if not state:
                click.echo(error("Invalid rebase state"))
                clear_rebase_state(repo)
                return
            
            # Create commit from current state
            current_commit_hash = state.commits[state.current_index]
            original_commit = repo.read_object(current_commit_hash)
            
            if isinstance(original_commit, Commit):
                new_hash = create_rebase_commit(repo, original_commit)
                click.echo(success(f"Applied: {current_commit_hash[:7]} → {new_hash[:7]}"))
            
            # Move to next commit
            state.current_index += 1
            
            if state.current_index >= len(state.commits):
                # Rebase complete
                clear_rebase_state(repo)
                click.echo(success("Rebase complete"))
                return
            
            # Save state and continue
            save_rebase_state(repo, state)
            
            # Apply remaining commits
            apply_remaining_commits(repo, state)
            return
        
        # Interactive rebase not implemented
        if interactive:
            click.echo(error("Interactive rebase not yet implemented"))
            return
        
        # Regular rebase
        if not upstream:
            click.echo(error("Missing argument 'UPSTREAM'"))
            click.echo(info("Usage: lit rebase <upstream>"))
            raise SystemExit(1)
        
        if is_rebase_in_progress(repo):
            click.echo(error("Rebase already in progress"))
            click.echo(info("Use 'lit rebase --continue', '--skip', or '--abort'"))
            raise SystemExit(1)
        
        # Resolve upstream reference
        onto_hash = resolve_commit_ref(repo, upstream)
        if not onto_hash:
            click.echo(error(f"'{upstream}' is not a valid commit or branch"))
            raise SystemExit(1)
        
        # Get current HEAD
        head = repo.refs.resolve_head()
        if not head:
            click.echo(error("No commits on current branch"))
            raise SystemExit(1)
        
        # Get current branch name
        head_content = (repo.lit_dir / 'HEAD').read_text().strip()
        if head_content.startswith('ref: refs/heads/'):
            head_name = head_content[16:]
        else:
            head_name = "(detached)"
        
        # Check if already up to date
        if head == onto_hash:
            click.echo(info("Already up to date"))
            return
        
        # Get commits to replay
        commits = get_commits_to_replay(repo, onto_hash, head)
        
        if not commits:
            # Fast-forward case
            update_head(repo, onto_hash)
            reset_to_commit(repo, onto_hash)
            click.echo(success(f"Fast-forwarded to {upstream}"))
            return
        
        click.echo(info(f"Rebasing {len(commits)} commit(s) onto {upstream}"))
        
        # Save rebase state
        state = RebaseState(
            onto=onto_hash,
            head_name=head_name,
            orig_head=head,
            commits=commits,
            current_index=0
        )
        save_rebase_state(repo, state)
        
        # Move HEAD to onto
        update_head(repo, onto_hash)
        reset_to_commit(repo, onto_hash)
        
        # Apply commits
        apply_remaining_commits(repo, state)
        
    except Exception as e:
        click.echo(error(f"Rebase failed: {e}"))


def apply_remaining_commits(repo, state: RebaseState) -> None:
    """Apply remaining commits in rebase."""
    while state.current_index < len(state.commits):
        commit_hash = state.commits[state.current_index]
        commit = repo.read_object(commit_hash)
        
        if not isinstance(commit, Commit):
            state.current_index += 1
            save_rebase_state(repo, state)
            continue
        
        click.echo(info(f"Applying: {commit_hash[:7]} {commit.message.split(chr(10))[0]}"))
        
        new_hash, conflicts = apply_commit_three_way(repo, commit_hash)
        
        if conflicts:
            save_rebase_state(repo, state)
            click.echo(warning("Conflict detected"))
            click.echo(info("Conflicts in:"))
            for conflict in conflicts:
                click.echo(f"  {Fore.RED}{conflict.path}{Style.RESET_ALL}")
            click.echo()
            click.echo(info("Resolve conflicts, then run 'lit rebase --continue'"))
            click.echo(info("Or 'lit rebase --skip' to skip this commit"))
            click.echo(info("Or 'lit rebase --abort' to cancel rebase"))
            return
        
        if new_hash == "skip":
            click.echo(info(f"  (empty commit, skipped)"))
        else:
            click.echo(success(f"  → {new_hash[:7]}"))
        
        state.current_index += 1
        save_rebase_state(repo, state)
    
    # Rebase complete
    clear_rebase_state(repo)
    click.echo(success("Rebase complete"))
