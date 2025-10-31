"""Unit tests for reference management."""

import pytest
from lit.core.refs import RefManager
from lit.core.objects import Commit


def test_ref_manager_init(repo):
    """Test RefManager initialization."""
    refs = RefManager(repo)
    assert refs.repo == repo
    assert refs.lit_dir == repo.lit_dir


def test_get_current_branch_on_main(repo):
    """Test getting current branch when on main."""
    # Set HEAD to main
    repo.head_file.write_text("ref: refs/heads/main\n")
    refs = RefManager(repo)
    assert refs.get_current_branch() == "main"


def test_get_current_branch_detached(repo):
    """Test getting current branch in detached HEAD state."""
    # Set HEAD to a commit hash (detached)
    fake_hash = "a" * 40
    repo.head_file.write_text(fake_hash + "\n")
    refs = RefManager(repo)
    assert refs.get_current_branch() is None


def test_is_detached_head(repo):
    """Test detecting detached HEAD state."""
    refs = RefManager(repo)
    
    # Symbolic reference - not detached
    repo.head_file.write_text("ref: refs/heads/main\n")
    assert refs.is_detached_head() is False
    
    # Direct reference - detached
    fake_hash = "a" * 40
    repo.head_file.write_text(fake_hash + "\n")
    assert refs.is_detached_head() is True


def test_create_branch(repo, sample_commit):
    """Test creating a new branch."""
    refs = RefManager(repo)
    commit_hash = repo.write_object(sample_commit)
    
    # Create branch
    result = refs.create_branch("feature", commit_hash)
    assert result is True
    
    # Verify branch file exists
    branch_file = repo.lit_dir / 'refs' / 'heads' / 'feature'
    assert branch_file.exists()
    assert branch_file.read_text().strip() == commit_hash


def test_create_branch_already_exists(repo, sample_commit):
    """Test creating a branch that already exists."""
    refs = RefManager(repo)
    commit_hash = repo.write_object(sample_commit)
    
    # Create branch
    refs.create_branch("feature", commit_hash)
    
    # Try to create again - should fail
    result = refs.create_branch("feature", commit_hash)
    assert result is False


def test_delete_branch(repo, sample_commit):
    """Test deleting a branch."""
    refs = RefManager(repo)
    commit_hash = repo.write_object(sample_commit)
    
    # Create and delete branch
    refs.create_branch("feature", commit_hash)
    result = refs.delete_branch("feature")
    assert result is True
    
    # Verify branch file is gone
    branch_file = repo.lit_dir / 'refs' / 'heads' / 'feature'
    assert not branch_file.exists()


def test_delete_current_branch_fails(repo, sample_commit):
    """Test that deleting current branch fails."""
    refs = RefManager(repo)
    commit_hash = repo.write_object(sample_commit)
    
    # Create and switch to branch
    refs.create_branch("feature", commit_hash)
    refs.set_head("feature", symbolic=True)
    
    # Try to delete current branch - should fail
    result = refs.delete_branch("feature")
    assert result is False


def test_list_branches(repo, sample_commit):
    """Test listing all branches."""
    refs = RefManager(repo)
    commit_hash = repo.write_object(sample_commit)
    
    # Create multiple branches
    refs.create_branch("main", commit_hash)
    refs.create_branch("feature", commit_hash)
    refs.create_branch("bugfix", commit_hash)
    
    branches = refs.list_branches()
    branch_names = [name for name, _ in branches]
    
    assert "main" in branch_names
    assert "feature" in branch_names
    assert "bugfix" in branch_names


def test_resolve_reference_full_hash(repo, sample_commit):
    """Test resolving a full commit hash."""
    refs = RefManager(repo)
    commit_hash = repo.write_object(sample_commit)
    
    resolved = refs.resolve_reference(commit_hash)
    assert resolved == commit_hash


def test_resolve_reference_branch(repo, sample_commit):
    """Test resolving a branch reference."""
    refs = RefManager(repo)
    commit_hash = repo.write_object(sample_commit)
    refs.create_branch("main", commit_hash)
    
    resolved = refs.resolve_reference("main")
    assert resolved == commit_hash


def test_set_head_symbolic(repo, sample_commit):
    """Test setting HEAD to a branch (symbolic)."""
    refs = RefManager(repo)
    commit_hash = repo.write_object(sample_commit)
    refs.create_branch("main", commit_hash)
    
    result = refs.set_head("main", symbolic=True)
    assert result is True
    
    content = repo.head_file.read_text().strip()
    assert content == "ref: refs/heads/main"


def test_set_head_detached(repo, sample_commit):
    """Test setting HEAD to a commit (detached)."""
    refs = RefManager(repo)
    commit_hash = repo.write_object(sample_commit)
    
    result = refs.set_head(commit_hash, symbolic=False)
    assert result is True
    
    content = repo.head_file.read_text().strip()
    assert content == commit_hash


def test_get_ref_info_head_symbolic(repo, sample_commit):
    """Test getting reference info for symbolic HEAD."""
    refs = RefManager(repo)
    commit_hash = repo.write_object(sample_commit)
    refs.create_branch("main", commit_hash)
    refs.set_head("main", symbolic=True)
    
    info = refs.get_ref_info("HEAD")
    assert info['exists'] is True
    assert info['type'] == 'HEAD'
    assert info['symbolic'] is True
    assert info['symbolic_target'] == 'refs/heads/main'
    assert info['target'] == commit_hash


def test_get_ref_info_head_detached(repo, sample_commit):
    """Test getting reference info for detached HEAD."""
    refs = RefManager(repo)
    commit_hash = repo.write_object(sample_commit)
    refs.set_head(commit_hash, symbolic=False)
    
    info = refs.get_ref_info("HEAD")
    assert info['exists'] is True
    assert info['type'] == 'HEAD'
    assert info['symbolic'] is False
    assert info['target'] == commit_hash
