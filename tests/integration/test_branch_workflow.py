"""Integration tests for branch management workflow."""

import pytest
from pathlib import Path
from tests.conftest import make_commit


def test_create_branch_on_commit(repo_with_commits):
    """Test creating a branch on an existing commit."""
    repo = repo_with_commits
    
    # Get HEAD commit
    head_hash = repo.refs.resolve_head()
    
    # Create branch
    result = repo.refs.create_branch("feature", head_hash)
    assert result is True
    
    # Verify branch exists
    branches = repo.refs.list_branches()
    branch_names = [name for name, _ in branches]
    assert "feature" in branch_names


def test_switch_between_branches(repo_with_commits):
    """Test switching between branches."""
    repo = repo_with_commits
    refs = repo.refs
    
    # Create and switch to feature branch
    head_hash = repo.refs.resolve_head()
    refs.create_branch("feature", head_hash)
    refs.set_head("feature", symbolic=True)
    
    # Verify on feature branch
    assert refs.get_current_branch() == "feature"
    
    # Switch back to main
    refs.create_branch("main", head_hash)
    refs.set_head("main", symbolic=True)
    
    # Verify on main branch
    assert refs.get_current_branch() == "main"


def test_commit_on_different_branch(repo_with_commits):
    """Test committing on different branches creates divergent history."""
    repo = repo_with_commits
    refs = repo.refs
    
    # Get initial commit
    initial_hash = repo.refs.resolve_head()
    
    # Create and switch to feature branch
    refs.create_branch("feature", initial_hash)
    refs.set_head("feature", symbolic=True)
    
    # Make commit on feature
    file1 = repo.work_tree / "feature.txt"
    file1.write_text("feature work")
    repo.index.add_file(repo, file1)
    feature_commit = make_commit(repo, "Feature work")
    
    # Switch to main
    refs.create_branch("main", initial_hash)
    refs.set_head("main", symbolic=True)
    
    # Make commit on main
    file2 = repo.work_tree / "main.txt"
    file2.write_text("main work")
    repo.index.add_file(repo, file2)
    main_commit = make_commit(repo, "Main work")
    
    # Verify commits are different
    assert feature_commit != main_commit
    
    # Verify both point to initial commit as parent
    feature_obj = repo.read_object(feature_commit)
    main_obj = repo.read_object(main_commit)
    assert feature_obj.parents[0] == initial_hash
    assert main_obj.parents[0] == initial_hash


def test_delete_branch(repo_with_commits):
    """Test deleting a branch."""
    repo = repo_with_commits
    refs = repo.refs
    
    # Create branch
    head_hash = repo.refs.resolve_head()
    refs.create_branch("temp", head_hash)
    
    # Verify it exists
    branches = refs.list_branches()
    branch_names = [name for name, _ in branches]
    assert "temp" in branch_names
    
    # Delete it
    result = refs.delete_branch("temp")
    assert result is True
    
    # Verify it's gone
    branches = refs.list_branches()
    branch_names = [name for name, _ in branches]
    assert "temp" not in branch_names


def test_cannot_delete_current_branch(repo_with_commits):
    """Test that deleting current branch fails."""
    repo = repo_with_commits
    refs = repo.refs
    
    # Create and switch to branch
    head_hash = repo.refs.resolve_head()
    refs.create_branch("current", head_hash)
    refs.set_head("current", symbolic=True)
    
    # Try to delete current branch
    result = refs.delete_branch("current")
    assert result is False


def test_detached_head_state(repo_with_commits):
    """Test entering and working in detached HEAD state."""
    repo = repo_with_commits
    refs = repo.refs
    
    # Get a commit hash
    head_hash = repo.refs.resolve_head()
    
    # Enter detached HEAD
    refs.set_head(head_hash, symbolic=False)
    
    # Verify detached
    assert refs.is_detached_head() is True
    assert refs.get_current_branch() is None
    
    # Make a commit in detached HEAD
    file1 = repo.work_tree / "detached.txt"
    file1.write_text("detached work")
    repo.index.add_file(repo, file1)
    detached_commit = make_commit(repo, "Detached commit")
    
    # Verify commit was created
    assert detached_commit is not None
    
    # Verify HEAD moved to new commit
    new_head = repo.refs.resolve_head()
    assert new_head == detached_commit


def test_branch_listing_shows_all_branches(repo_with_commits):
    """Test that branch listing shows all created branches."""
    repo = repo_with_commits
    refs = repo.refs
    
    head_hash = repo.refs.resolve_head()
    
    # Create multiple branches
    refs.create_branch("main", head_hash)
    refs.create_branch("feature1", head_hash)
    refs.create_branch("feature2", head_hash)
    refs.create_branch("bugfix", head_hash)
    
    # List branches
    branches = refs.list_branches()
    branch_names = [name for name, _ in branches]
    
    # Verify all exist
    assert "main" in branch_names
    assert "feature1" in branch_names
    assert "feature2" in branch_names
    assert "bugfix" in branch_names
    assert len(branch_names) == 4


def test_branch_resolution(repo_with_commits):
    """Test resolving branch references to commit hashes."""
    repo = repo_with_commits
    refs = repo.refs
    
    head_hash = repo.refs.resolve_head()
    refs.create_branch("test", head_hash)
    
    # Resolve branch
    resolved = refs.resolve_reference("test")
    assert resolved == head_hash
