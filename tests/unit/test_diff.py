"""Unit tests for diff engine."""

import pytest
from pathlib import Path
from lit.operations.diff import DiffEngine, DiffHunk, FileDiff
from lit.core.objects import Blob, Tree, TreeEntry


def test_diff_hunk_init():
    """Test DiffHunk initialization."""
    hunk = DiffHunk(
        old_start=1,
        old_count=3,
        new_start=1,
        new_count=5
    )
    assert hunk.old_start == 1
    assert hunk.old_count == 3
    assert hunk.new_start == 1
    assert hunk.new_count == 5
    assert len(hunk.lines) == 0
    
    # Test adding lines
    hunk.add_line("line1")
    hunk.add_line("line2")
    assert len(hunk.lines) == 2


def test_file_diff_new_file():
    """Test FileDiff for a new file."""
    diff = FileDiff(
        path="test.txt",
        old_content=None,
        new_content=b"hello"
    )
    assert diff.is_new is True
    assert diff.is_deleted is False
    assert diff.is_modified is False


def test_file_diff_deleted_file():
    """Test FileDiff for a deleted file."""
    diff = FileDiff(
        path="test.txt",
        old_content=b"hello",
        new_content=None
    )
    assert diff.is_new is False
    assert diff.is_deleted is True
    assert diff.is_modified is False


def test_file_diff_modified_file():
    """Test FileDiff for a modified file."""
    diff = FileDiff(
        path="test.txt",
        old_content=b"hello",
        new_content=b"hello world"
    )
    assert diff.is_new is False
    assert diff.is_deleted is False
    assert diff.is_modified is True


def test_file_diff_compute_diff():
    """Test computing diff hunks."""
    diff = FileDiff(
        path="test.txt",
        old_content=b"line1\nline2\n",
        new_content=b"line1\nline2 modified\nline3\n"
    )
    diff.compute_diff()
    
    # Should have hunks
    assert len(diff.hunks) > 0


def test_diff_engine_init(repo):
    """Test DiffEngine initialization."""
    engine = DiffEngine(repo)
    assert engine.repo == repo


def test_diff_blobs_identical(repo):
    """Test diffing identical blobs."""
    engine = DiffEngine(repo)
    blob1 = Blob(b"hello world")
    blob2 = Blob(b"hello world")
    
    # diff_blobs expects bytes content, not hashes
    diff = engine.diff_blobs("test.txt", blob1.data, blob2.data)
    # Identical content returns a diff object
    assert diff is not None
    assert not diff.is_new
    assert not diff.is_deleted
    # is_modified just means both old and new exist, not that they're different
    assert diff.is_modified
    # But there should be no hunks for identical content
    assert len(diff.hunks) == 0


def test_diff_blobs_different(repo):
    """Test diffing different blobs."""
    engine = DiffEngine(repo)
    blob1 = Blob(b"hello")
    blob2 = Blob(b"hello world")
    
    # diff_blobs expects bytes content, not hashes
    diff = engine.diff_blobs("test.txt", blob1.data, blob2.data)
    assert diff is not None
    assert diff.is_modified is True


def test_diff_blobs_new_file(repo):
    """Test diffing when old blob is None (new file)."""
    engine = DiffEngine(repo)
    blob = Blob(b"hello world")
    
    # diff_blobs expects bytes content, not hashes
    diff = engine.diff_blobs("test.txt", None, blob.data)
    assert diff is not None
    assert diff.is_new is True


def test_diff_blobs_deleted_file(repo):
    """Test diffing when new blob is None (deleted file)."""
    engine = DiffEngine(repo)
    blob = Blob(b"hello world")
    
    # diff_blobs expects bytes content, not hashes
    diff = engine.diff_blobs("test.txt", blob.data, None)
    assert diff is not None
    assert diff.is_deleted is True


def test_diff_trees_identical(repo, sample_tree):
    """Test diffing identical trees."""
    engine = DiffEngine(repo)
    tree_hash = repo.write_object(sample_tree)
    
    # Get tree files dict using the helper method
    tree_files = engine._get_tree_files(sample_tree)
    
    diffs = engine.diff_trees(tree_files, tree_files)
    assert len(diffs) == 0


def test_diff_trees_different(repo):
    """Test diffing different trees."""
    engine = DiffEngine(repo)
    
    # Create two trees with different content
    blob1 = Blob(b"hello")
    blob2 = Blob(b"hello world")
    
    hash1 = repo.write_object(blob1)
    hash2 = repo.write_object(blob2)
    
    # Create trees with proper add_entry method (not TreeEntry directly)
    tree1 = Tree()
    tree1.add_entry("100644", "blob", hash1, "test.txt")
    
    tree2 = Tree()
    tree2.add_entry("100644", "blob", hash2, "test.txt")
    
    # Get tree files dicts
    tree1_files = engine._get_tree_files(tree1)
    tree2_files = engine._get_tree_files(tree2)
    
    diffs = engine.diff_trees(tree1_files, tree2_files)
    assert len(diffs) == 1
    assert diffs[0].path == "test.txt"
    assert diffs[0].is_modified is True


def test_diff_working_to_index(repo_with_config):
    """Test diffing working directory to index."""
    repo = repo_with_config
    engine = DiffEngine(repo)
    
    # Add a file to index
    test_file = repo.work_tree / "test.txt"
    test_file.write_text("hello")
    repo.index.add_file(repo, test_file)
    
    # Modify the file
    test_file.write_text("hello world")
    
    diffs = engine.diff_working_to_index()
    assert len(diffs) == 1
    assert diffs[0].path == "test.txt"
    assert diffs[0].is_modified is True


def test_diff_index_to_head(repo_with_commits):
    """Test diffing index to HEAD."""
    repo = repo_with_commits
    engine = DiffEngine(repo)
    
    # Create an index and modify a file
    from lit.core.index import Index
    index = Index()
    
    test_file = repo.work_tree / "file1.txt"
    test_file.write_text("modified content")
    index.add_file(repo, test_file)
    
    diffs = engine.diff_index_to_head()
    # repo_with_commits has file1.txt and file2.txt
    # We only modified file1.txt, so we should see 1 modified file
    # But file2.txt is in HEAD and not in our new index, so it appears deleted
    # Let's add file2.txt back to the index
    file2 = repo.work_tree / "file2.txt"
    index.add_file(repo, file2)
    
    diffs = engine.diff_index_to_head()
    assert len(diffs) == 1
    assert diffs[0].path == "file1.txt"
    assert diffs[0].is_modified is True


def test_format_diff_new_file(repo):
    """Test formatting diff for new file."""
    engine = DiffEngine(repo)
    diff = FileDiff(
        path="test.txt",
        old_content=None,
        new_content=b"hello\nworld\n"
    )
    diff.compute_diff()
    
    output = engine.format_diff([diff], color=False)
    assert "new file" in output
    assert "+hello" in output
    assert "+world" in output


def test_format_diff_deleted_file(repo):
    """Test formatting diff for deleted file."""
    engine = DiffEngine(repo)
    diff = FileDiff(
        path="test.txt",
        old_content=b"hello\nworld\n",
        new_content=None
    )
    diff.compute_diff()
    
    output = engine.format_diff([diff], color=False)
    assert "deleted file" in output
    assert "-hello" in output
    assert "-world" in output


def test_format_diff_modified_file(repo):
    """Test formatting diff for modified file."""
    engine = DiffEngine(repo)
    diff = FileDiff(
        path="test.txt",
        old_content=b"hello\n",
        new_content=b"hello world\n"
    )
    diff.compute_diff()
    
    output = engine.format_diff([diff], color=False)
    assert "--- a/test.txt" in output
    assert "+++ b/test.txt" in output
    assert "-hello" in output
    assert "+hello world" in output
