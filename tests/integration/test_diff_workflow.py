"""Integration tests for diff workflow."""

import pytest
from pathlib import Path
from tests.conftest import make_commit


def test_diff_working_vs_index(repo_with_commits):
    """Test diffing working directory vs index."""
    repo = repo_with_commits
    engine = repo.diff
    
    # Modify a file without staging
    file1 = repo.work_tree / "file1.txt"
    file1.write_text("modified content")
    
    # Get diff
    diffs = engine.diff_working_to_index()
    
    # Find the file1.txt diff
    file1_diff = next((d for d in diffs if d.path == "file1.txt"), None)
    assert file1_diff is not None
    assert file1_diff.is_modified is True


def test_diff_index_vs_head(repo_with_commits):
    """Test diffing index vs HEAD."""
    repo = repo_with_commits
    engine = repo.diff
    
    # Modify and stage a file
    file1 = repo.work_tree / "file1.txt"
    file1.write_text("staged content")
    repo.index.add_file(repo, file1)
    
    # Get diff
    diffs = engine.diff_index_to_head()
    
    # Find the file1.txt diff
    file1_diff = next((d for d in diffs if d.path == "file1.txt"), None)
    assert file1_diff is not None
    assert file1_diff.is_modified is True


def test_diff_new_file_workflow(repo_with_commits):
    """Test diff workflow for new file."""
    repo = repo_with_commits
    engine = repo.diff
    
    # Create new file
    new_file = repo.work_tree / "new.txt"
    new_file.write_text("new content")
    
    # Stage it
    repo.index.add_file(repo, new_file)
    
    # Diff index vs HEAD should show new file
    diffs = engine.diff_index_to_head()
    
    new_diff = next((d for d in diffs if d.path == "new.txt"), None)
    assert new_diff is not None
    assert new_diff.is_new is True


def test_diff_deleted_file_workflow(repo_with_commits):
    """Test diff workflow for deleted file."""
    repo = repo_with_commits
    engine = repo.diff
    
    # Delete a file that's in HEAD
    file1 = repo.work_tree / "file1.txt"
    file1.unlink()
    
    # Update index to reflect deletion
    repo.index.remove_entry("file1.txt", repo)
    
    # Diff index vs HEAD should show deleted file
    diffs = engine.diff_index_to_head()
    
    deleted_diff = next((d for d in diffs if d.path == "file1.txt"), None)
    assert deleted_diff is not None
    assert deleted_diff.is_deleted is True


def test_diff_between_commits(repo_with_commits):
    """Test diffing between two commits."""
    repo = repo_with_commits
    engine = repo.diff
    
    # Get the two existing commits
    commit2_hash = repo.refs.resolve_head()
    commit2 = repo.read_object(commit2_hash)
    commit1_hash = commit2.parents[0]
    
    # Diff between commits
    diffs = engine.diff_commits(commit1_hash, commit2_hash)
    
    # Should show file2.txt as new
    assert len(diffs) == 1
    assert diffs[0].path == "file2.txt"
    assert diffs[0].is_new is True


def test_diff_format_output(repo_with_commits):
    """Test that diff formatting produces valid output."""
    repo = repo_with_commits
    engine = repo.diff
    
    # Modify a file
    file1 = repo.work_tree / "file1.txt"
    original_content = file1.read_text()
    file1.write_text(original_content + "\nadded line")
    
    # Get diff
    diffs = engine.diff_working_to_index()
    
    # Format diff
    output = engine.format_diff(diffs, color=False)
    
    # Verify standard diff format
    assert "diff --lit" in output
    assert "a/file1.txt" in output
    assert "b/file1.txt" in output
    assert "+added line" in output


def test_diff_unstaged_and_staged_changes(repo_with_commits):
    """Test distinguishing unstaged vs staged changes."""
    repo = repo_with_commits
    engine = repo.diff
    
    # Modify file1, stage it
    file1 = repo.work_tree / "file1.txt"
    file1.write_text("staged change")
    repo.index.add_file(repo, file1)
    
    # Modify file1 again without staging
    file1.write_text("unstaged change")
    
    # Diff working vs index should show unstaged change
    unstaged_diffs = engine.diff_working_to_index()
    file1_diff = next((d for d in unstaged_diffs if d.path == "file1.txt"), None)
    assert file1_diff is not None
    assert b"unstaged change" in file1_diff.new_content
    
    # Diff index vs HEAD should show staged change
    staged_diffs = engine.diff_index_to_head()
    file1_staged = next((d for d in staged_diffs if d.path == "file1.txt"), None)
    assert file1_staged is not None
    # Note: staged diff shows what's in index, which was "staged change"


def test_diff_with_commit_chain(repo_with_commits):
    """Test diffing with longer commit history."""
    repo = repo_with_commits
    engine = repo.diff
    
    # Make third commit
    file3 = repo.work_tree / "file3.txt"
    file3.write_text("content 3")
    repo.index.add_file(repo, file3)
    commit3 = make_commit(repo, "Third commit")
    
    # Get commit chain
    commit3_obj = repo.read_object(commit3)
    commit2_hash = commit3_obj.parents[0]
    commit2_obj = repo.read_object(commit2_hash)
    commit1_hash = commit2_obj.parents[0]
    
    # Diff commit1 vs commit3 should show file2 and file3 as new
    diffs = engine.diff_commits(commit1_hash, commit3)
    
    new_files = [d.path for d in diffs if d.is_new]
    assert "file2.txt" in new_files
    assert "file3.txt" in new_files


def test_no_diff_for_identical_content(repo_with_commits):
    """Test that no diff is shown for identical content."""
    repo = repo_with_commits
    engine = repo.diff
    
    # Working directory matches index (from repo_with_commits fixture)
    # So working vs index should show no diffs initially
    
    # Note: repo_with_commits has file1.txt and file2.txt
    # They should be identical in working, index, and HEAD
    
    # Actually, let's verify by not changing anything
    head_hash = repo.refs.resolve_head()
    diffs = engine.diff_commits(head_hash, head_hash)
    
    # Same commit should have no diffs
    assert len(diffs) == 0
