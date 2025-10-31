"""Integration tests for add and commit workflow."""

import pytest
from pathlib import Path
from tests.conftest import make_commit


def test_add_and_commit_single_file(repo_with_config):
    """Test adding and committing a single file."""
    repo = repo_with_config
    
    # Create and add file
    test_file = repo.work_tree / "test.txt"
    test_file.write_text("hello world")
    repo.index.add_file(repo, test_file)
    
    # Verify file is staged
    entries = list(repo.index.entries.values())
    assert len(entries) == 1
    assert entries[0].path == "test.txt"
    
    # Commit
    commit_hash = make_commit(repo, "Initial commit")
    assert commit_hash is not None
    
    # Verify HEAD points to commit
    head_hash = repo.refs.resolve_head()
    assert head_hash == commit_hash


def test_add_and_commit_multiple_files(repo_with_config):
    """Test adding and committing multiple files."""
    repo = repo_with_config
    
    # Create and add multiple files
    file1 = repo.work_tree / "file1.txt"
    file2 = repo.work_tree / "file2.txt"
    file3 = repo.work_tree / "file3.txt"
    
    file1.write_text("content 1")
    file2.write_text("content 2")
    file3.write_text("content 3")
    
    repo.index.add_file(repo, file1)
    repo.index.add_file(repo, file2)
    repo.index.add_file(repo, file3)
    
    # Verify all files are staged
    assert len(repo.index.entries) == 3
    
    # Commit
    commit_hash = make_commit(repo, "Add multiple files")
    assert commit_hash is not None


def test_commit_chain(repo_with_config):
    """Test creating a chain of commits."""
    repo = repo_with_config
    
    # First commit
    file1 = repo.work_tree / "file1.txt"
    file1.write_text("version 1")
    repo.index.add_file(repo, file1)
    commit1 = make_commit(repo, "First commit")
    
    # Second commit
    file1.write_text("version 2")
    repo.index.add_file(repo, file1)
    commit2 = make_commit(repo, "Second commit")
    
    # Third commit
    file1.write_text("version 3")
    repo.index.add_file(repo, file1)
    commit3 = make_commit(repo, "Third commit")
    
    # Verify commit chain
    commit_obj3 = repo.read_object(commit3)
    assert commit_obj3.parents[0] == commit2
    
    commit_obj2 = repo.read_object(commit2)
    assert commit_obj2.parents[0] == commit1
    
    commit_obj1 = repo.read_object(commit1)
    assert len(commit_obj1.parents) == 0


def test_nested_directory_structure(repo_with_config):
    """Test adding and committing files in nested directories."""
    repo = repo_with_config
    
    # Create nested structure
    (repo.work_tree / "src").mkdir()
    (repo.work_tree / "src" / "lib").mkdir()
    
    file1 = repo.work_tree / "src" / "main.py"
    file2 = repo.work_tree / "src" / "lib" / "utils.py"
    
    file1.write_text("# main")
    file2.write_text("# utils")
    
    repo.index.add_file(repo, file1)
    repo.index.add_file(repo, file2)
    
    # Commit
    commit_hash = make_commit(repo, "Add nested files")
    assert commit_hash is not None
    
    # Verify both files are in commit
    commit_obj = repo.read_object(commit_hash)
    tree_obj = repo.read_object(commit_obj.tree)
    
    # Should have src directory entry
    src_entry = next((e for e in tree_obj.entries if e.name == "src"), None)
    assert src_entry is not None


def test_modify_and_recommit(repo_with_config):
    """Test modifying a file and committing again."""
    repo = repo_with_config
    
    # Initial commit
    test_file = repo.work_tree / "test.txt"
    test_file.write_text("version 1")
    repo.index.add_file(repo, test_file)
    commit1 = make_commit(repo, "Initial version")
    
    # Modify and commit again
    test_file.write_text("version 2")
    repo.index.add_file(repo, test_file)
    commit2 = make_commit(repo, "Updated version")
    
    # Verify both commits have different content
    commit_obj1 = repo.read_object(commit1)
    tree_obj1 = repo.read_object(commit_obj1.tree)
    entry1 = tree_obj1.entries[0]
    blob1 = repo.read_object(entry1.hash)
    
    commit_obj2 = repo.read_object(commit2)
    tree_obj2 = repo.read_object(commit_obj2.tree)
    entry2 = tree_obj2.entries[0]
    blob2 = repo.read_object(entry2.hash)
    
    assert blob1.data != blob2.data
    assert blob1.data == b"version 1"
    assert blob2.data == b"version 2"


def test_index_after_commit(repo_with_config):
    """Test that index matches HEAD after commit."""
    repo = repo_with_config
    
    # Add and commit file
    test_file = repo.work_tree / "test.txt"
    test_file.write_text("hello")
    repo.index.add_file(repo, test_file)
    commit_hash = make_commit(repo, "Test commit")
    
    # Get tree from commit
    commit_obj = repo.read_object(commit_hash)
    tree_hash = commit_obj.tree
    
    # Compare with index
    entry = list(repo.index.entries.values())[0]
    tree_obj = repo.read_object(tree_hash)
    tree_entry = tree_obj.entries[0]
    
    # Index should have same content hash as tree
    assert entry.sha1 == tree_entry.hash


def test_empty_commit_fails(repo_with_config):
    """Test that committing with no staged files fails."""
    repo = repo_with_config
    
    # Try to commit with nothing staged
    commit_hash = make_commit(repo, "Empty commit")
    assert commit_hash is None
