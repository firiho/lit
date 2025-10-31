"""Unit tests for merge operations."""

import pytest
from pathlib import Path
from lit.core.repository import Repository
from lit.core.merge import MergeEngine, MergeResult, MergeConflict
from lit.core.objects import Commit, Tree, Blob
from lit.core.index import Index
from tests.conftest import make_commit


def test_merge_engine_initialization(repo):
    """Test MergeEngine initialization."""
    engine = repo.merge
    assert isinstance(engine, MergeEngine)
    assert engine.repo == repo


def test_find_merge_base_same_commit(repo_with_commits):
    """Test finding merge base when commits are the same."""
    repo = repo_with_commits
    commit_hash = repo.refs.resolve_head()
    
    merge_base = repo.merge.find_merge_base(commit_hash, commit_hash)
    assert merge_base == commit_hash


def test_find_merge_base_direct_ancestor(repo_with_commits):
    """Test finding merge base when one commit is ancestor of the other."""
    repo = repo_with_commits
    
    # Get the commit chain
    commit2_hash = repo.refs.resolve_head()
    commit2 = repo.read_object(commit2_hash)
    commit1_hash = commit2.parents[0]
    
    # Merge base should be commit1 (the ancestor)
    merge_base = repo.merge.find_merge_base(commit1_hash, commit2_hash)
    assert merge_base == commit1_hash


def test_find_merge_base_diverged_branches(repo_with_commits):
    """Test finding merge base with diverged branches."""
    repo = repo_with_commits
    
    # Get initial commit
    commit2_hash = repo.refs.resolve_head()
    commit2 = repo.read_object(commit2_hash)
    commit1_hash = commit2.parents[0]
    
    # Create a branch at commit1
    repo.refs.create_branch("feature", commit1_hash)
    
    # Make a commit on main (already at commit2)
    file1 = repo.work_tree / "file1.txt"
    file1.write_text("main branch change")
    repo.index.add_file(repo, file1)
    main_commit = make_commit(repo, "Main change")
    
    # Switch to feature and make a commit
    repo.refs.set_head("feature")
    file2 = repo.work_tree / "file2.txt"
    file2.write_text("feature branch change")
    repo.index.add_file(repo, file2)
    feature_commit = make_commit(repo, "Feature change")
    
    # Find merge base
    merge_base = repo.merge.find_merge_base(main_commit, feature_commit)
    assert merge_base == commit1_hash


def test_can_fast_forward_true(repo_with_commits):
    """Test fast-forward detection when possible."""
    repo = repo_with_commits
    
    # Get commit chain
    commit2_hash = repo.refs.resolve_head()
    commit2 = repo.read_object(commit2_hash)
    commit1_hash = commit2.parents[0]
    
    # commit2 is descendant of commit1, so fast-forward is possible
    assert repo.merge.can_fast_forward(commit1_hash, commit2_hash) is True


def test_can_fast_forward_false(repo_with_commits):
    """Test fast-forward detection when not possible."""
    repo = repo_with_commits
    
    # Get initial commit
    commit2_hash = repo.refs.resolve_head()
    commit2 = repo.read_object(commit2_hash)
    commit1_hash = commit2.parents[0]
    
    # Create diverged branches
    repo.refs.create_branch("branch1", commit1_hash)
    repo.refs.create_branch("branch2", commit1_hash)
    
    # Make commit on branch1
    repo.refs.set_head("branch1")
    file1 = repo.work_tree / "file1.txt"
    file1.write_text("branch1 change")
    repo.index.add_file(repo, file1)
    branch1_commit = make_commit(repo, "Branch1 change")
    
    # Make commit on branch2
    repo.refs.set_head("branch2")
    file2 = repo.work_tree / "file2.txt"
    file2.write_text("branch2 change")
    repo.index.add_file(repo, file2)
    branch2_commit = make_commit(repo, "Branch2 change")
    
    # Can't fast-forward between diverged branches
    assert repo.merge.can_fast_forward(branch1_commit, branch2_commit) is False


def test_fast_forward_merge(repo_with_commits):
    """Test fast-forward merge operation."""
    repo = repo_with_commits
    
    # Get commit chain
    commit2_hash = repo.refs.resolve_head()
    commit2 = repo.read_object(commit2_hash)
    commit1_hash = commit2.parents[0]
    
    # Reset to commit1
    repo.refs.write_ref("refs/heads/main", commit1_hash)
    repo.head_file.write_text("ref: refs/heads/main\n")
    
    # Fast-forward to commit2
    result = repo.merge.fast_forward(commit2_hash)
    
    assert result.success is True
    assert result.is_fast_forward is True
    assert len(result.conflicts) == 0
    assert repo.refs.resolve_head() == commit2_hash


def test_three_way_merge_no_conflicts(repo_with_commits):
    """Test three-way merge without conflicts."""
    repo = repo_with_commits
    
    # Get base commit
    commit2_hash = repo.refs.resolve_head()
    commit2 = repo.read_object(commit2_hash)
    base_hash = commit2.parents[0]
    
    # Create two branches from base
    repo.refs.create_branch("branch1", base_hash)
    repo.refs.create_branch("branch2", base_hash)
    
    # Make non-conflicting change on branch1
    repo.refs.set_head("branch1")
    file1 = repo.work_tree / "file1.txt"
    file1.write_text("branch1 change")
    repo.index.add_file(repo, file1)
    branch1_commit = make_commit(repo, "Branch1 change")
    
    # Make non-conflicting change on branch2 (different file)
    repo.refs.set_head("branch2")
    file3 = repo.work_tree / "file3.txt"
    file3.write_text("branch2 change")
    repo.index.add_file(repo, file3)
    branch2_commit = make_commit(repo, "Branch2 change")
    
    # Perform three-way merge
    result = repo.merge.three_way_merge(base_hash, branch1_commit, branch2_commit)
    
    assert result.success is True
    assert len(result.conflicts) == 0
    assert result.merged_tree_hash is not None


def test_three_way_merge_with_conflicts(repo_with_commits):
    """Test three-way merge with conflicts."""
    repo = repo_with_commits
    
    # Get base commit
    commit2_hash = repo.refs.resolve_head()
    commit2 = repo.read_object(commit2_hash)
    base_hash = commit2.parents[0]
    
    # Create two branches from base
    repo.refs.create_branch("branch1", base_hash)
    repo.refs.create_branch("branch2", base_hash)
    
    # Make conflicting change on branch1
    repo.refs.set_head("branch1")
    file1 = repo.work_tree / "file1.txt"
    file1.write_text("branch1 version")
    repo.index.add_file(repo, file1)
    branch1_commit = make_commit(repo, "Branch1 change")
    
    # Make conflicting change on branch2 (same file)
    repo.refs.set_head("branch2")
    file1.write_text("branch2 version")
    repo.index.add_file(repo, file1)
    branch2_commit = make_commit(repo, "Branch2 change")
    
    # Perform three-way merge
    result = repo.merge.three_way_merge(base_hash, branch1_commit, branch2_commit)
    
    assert result.success is False
    assert len(result.conflicts) > 0
    assert result.conflicts[0].path == "file1.txt"


def test_merge_command_fast_forward(repo_with_commits):
    """Test high-level merge command with fast-forward."""
    repo = repo_with_commits
    
    # Get current commit
    commit2_hash = repo.refs.resolve_head()
    commit2 = repo.read_object(commit2_hash)
    commit1_hash = commit2.parents[0]
    
    # Create feature branch at commit2
    repo.refs.create_branch("feature", commit2_hash)
    
    # Reset main to commit1 and make sure HEAD follows
    repo.refs.write_ref("refs/heads/main", commit1_hash)
    repo.head_file.write_text("ref: refs/heads/main\n")
    
    # Merge feature into main (should fast-forward)
    result = repo.merge.merge("feature")
    
    assert result.success is True
    assert result.is_fast_forward is True
    assert repo.refs.resolve_head() == commit2_hash


def test_merge_command_no_fast_forward(repo_with_commits):
    """Test high-level merge command with no fast-forward."""
    repo = repo_with_commits
    
    # Get base commit
    commit2_hash = repo.refs.resolve_head()
    commit2 = repo.read_object(commit2_hash)
    base_hash = commit2.parents[0]
    
    # Create feature branch from base
    repo.refs.create_branch("feature", base_hash)
    
    # Make change on main
    file1 = repo.work_tree / "file1.txt"
    file1.write_text("main change")
    repo.index.add_file(repo, file1)
    make_commit(repo, "Main change")
    
    # Make change on feature
    repo.refs.set_head("feature")
    file3 = repo.work_tree / "file3.txt"
    file3.write_text("feature change")
    repo.index.add_file(repo, file3)
    make_commit(repo, "Feature change")
    
    # Switch back to main and merge
    repo.refs.set_head("main")
    result = repo.merge.merge("feature", allow_fast_forward=False)
    
    assert result.success is True
    assert result.is_fast_forward is False


def test_merge_already_up_to_date(repo_with_commits):
    """Test merge when already up to date."""
    repo = repo_with_commits
    
    # Create branch at current commit
    current_hash = repo.refs.resolve_head()
    repo.refs.create_branch("feature", current_hash)
    
    # Try to merge (should be up to date)
    result = repo.merge.merge("feature")
    
    assert result.success is True
    assert "up to date" in result.message.lower()


def test_merge_nonexistent_branch(repo_with_commits):
    """Test merge with nonexistent branch."""
    repo = repo_with_commits
    
    result = repo.merge.merge("nonexistent")
    
    assert result.success is False
    assert "not found" in result.message


def test_merge_conflict_representation():
    """Test MergeConflict string representation."""
    conflict = MergeConflict(
        path="test.txt",
        base_content=b"base",
        ours_content=b"ours",
        theirs_content=b"theirs"
    )
    
    assert "test.txt" in str(conflict)


def test_merge_result_representation():
    """Test MergeResult string representation."""
    # Success
    result = MergeResult(success=True, conflicts=[])
    assert "success" in str(result).lower()
    
    # Fast-forward
    result = MergeResult(success=True, conflicts=[], is_fast_forward=True)
    assert "fast-forward" in str(result).lower()
    
    # Failed
    result = MergeResult(success=False, conflicts=[])
    assert "failed" in str(result).lower()


def test_get_ancestors(repo_with_commits):
    """Test getting all ancestors of a commit."""
    repo = repo_with_commits
    
    # Get current commit
    commit2_hash = repo.refs.resolve_head()
    commit2 = repo.read_object(commit2_hash)
    commit1_hash = commit2.parents[0]
    
    # Get ancestors of commit2
    ancestors = repo.merge._get_ancestors(commit2_hash)
    
    assert commit2_hash in ancestors
    assert commit1_hash in ancestors
    assert len(ancestors) >= 2


def test_distance_to_commit(repo_with_commits):
    """Test calculating distance between commits."""
    repo = repo_with_commits
    
    # Get commit chain
    commit2_hash = repo.refs.resolve_head()
    commit2 = repo.read_object(commit2_hash)
    commit1_hash = commit2.parents[0]
    
    # Distance from commit2 to commit1 should be 1
    distance = repo.merge._distance_to_commit(commit2_hash, commit1_hash)
    assert distance == 1
    
    # Distance from commit to itself should be 0
    distance = repo.merge._distance_to_commit(commit2_hash, commit2_hash)
    assert distance == 0


def test_auto_merge_line_based(repo):
    """Test automatic line-based merge."""
    base = b"line 1\nline 2\nline 3\n"
    ours = b"line 1\nline 2 modified\nline 3\n"
    theirs = b"line 1\nline 2\nline 3 modified\n"
    
    # Different lines modified - should auto-merge
    merged = repo.merge._try_auto_merge(base, ours, theirs)
    assert merged == b"line 1\nline 2 modified\nline 3 modified\n"


def test_auto_merge_conflict(repo):
    """Test automatic merge with conflicts."""
    base = b"line 1\nline 2\nline 3\n"
    ours = b"line 1\nours version\nline 3\n"
    theirs = b"line 1\ntheirs version\nline 3\n"
    
    # Same line modified - should conflict
    merged = repo.merge._try_auto_merge(base, ours, theirs)
    assert merged is None


def test_generate_conflict_markers(repo):
    """Test generating conflict markers."""
    ours = b"our version\n"
    theirs = b"their version\n"
    
    markers = repo.merge.generate_conflict_markers("test.txt", ours, theirs)
    
    assert b"<<<<<<< HEAD" in markers
    assert b"=======" in markers
    assert b">>>>>>> test.txt" in markers
    assert b"our version" in markers
    assert b"their version" in markers


def test_merge_state_tracking(repo_with_commits):
    """Test merge state save/clear/check."""
    repo = repo_with_commits
    
    # Initially no merge in progress
    assert repo.merge.is_merge_in_progress() is False
    assert repo.merge.get_merge_head() is None
    
    # Save merge state
    test_hash = "abc123"
    from lit.core.merge import MergeConflict
    conflicts = [MergeConflict("file.txt", b"base", b"ours", b"theirs")]
    
    repo.merge.save_merge_state(test_hash, conflicts)
    
    # Check merge is tracked
    assert repo.merge.is_merge_in_progress() is True
    assert repo.merge.get_merge_head() == test_hash
    
    # Clear merge state
    repo.merge.clear_merge_state()
    
    # Check merge is cleared
    assert repo.merge.is_merge_in_progress() is False
    assert repo.merge.get_merge_head() is None


def test_abort_merge(repo_with_commits):
    """Test aborting a merge."""
    repo = repo_with_commits
    
    # Can't abort when no merge in progress
    assert repo.merge.abort_merge() is False
    
    # Start a merge (simulate)
    test_hash = "abc123"
    from lit.core.merge import MergeConflict
    conflicts = [MergeConflict("file.txt", b"base", b"ours", b"theirs")]
    repo.merge.save_merge_state(test_hash, conflicts)
    
    # Now abort should work
    assert repo.merge.abort_merge() is True
    
    # Merge state should be cleared
    assert repo.merge.is_merge_in_progress() is False


def test_write_conflicts_to_working_tree(repo_with_commits):
    """Test writing conflict markers to files."""
    repo = repo_with_commits
    from lit.core.merge import MergeConflict
    
    # Create a conflict
    conflict = MergeConflict(
        path="conflict.txt",
        base_content=b"base content\n",
        ours_content=b"our changes\n",
        theirs_content=b"their changes\n"
    )
    
    # Write conflicts to working tree
    repo.merge.write_conflicts_to_working_tree([conflict])
    
    # Check file was created with markers
    conflict_file = repo.work_tree / "conflict.txt"
    assert conflict_file.exists()
    
    content = conflict_file.read_text()
    assert "<<<<<<< HEAD" in content
    assert "=======" in content
    assert ">>>>>>>" in content
    assert "our changes" in content
    assert "their changes" in content
