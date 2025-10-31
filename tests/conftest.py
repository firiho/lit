"""Shared pytest fixtures for Lit tests."""

import pytest
import tempfile
import shutil
from pathlib import Path
from collections import defaultdict
from lit.core.repository import Repository
from lit.core.objects import Blob, Tree, Commit
from lit.core.index import Index


def build_tree_from_index(repo, index):
    """
    Build tree object from index entries.
    Helper function for tests - creates tree structure from index.
    """
    trees = defaultdict(Tree)
    
    for path in sorted(index.entries.keys()):
        entry = index.entries[path]
        parts = Path(path).parts
        
        for i in range(len(parts)):
            dir_path = str(Path(*parts[:i])) if i > 0 else ''
            trees[dir_path]
        
        dir_path = str(Path(*parts[:-1])) if len(parts) > 1 else ''
        filename = parts[-1]
        
        mode = '100755' if entry.mode & 0o111 else '100644'
        trees[dir_path].add_entry(mode, 'blob', entry.sha1, filename)
    
    for dir_path in sorted(trees.keys(), key=lambda x: x.count('/'), reverse=True):
        if dir_path:
            tree = trees[dir_path]
            tree_hash = repo.write_object(tree)
            
            parent_parts = Path(dir_path).parts
            parent_path = str(Path(*parent_parts[:-1])) if len(parent_parts) > 1 else ''
            dir_name = parent_parts[-1]
            
            trees[parent_path].add_entry('040000', 'tree', tree_hash, dir_name)
    
    root_tree = trees['']
    tree_hash = repo.write_object(root_tree)
    return tree_hash


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def repo(temp_dir):
    """Create an initialized repository."""
    repo = Repository(str(temp_dir))
    repo.init()
    return repo


@pytest.fixture
def repo_with_config(repo):
    """Create a repository with config set."""
    config_file = repo.config_file
    config_file.write_text("""[user]
\tname = Test User
\temail = test@example.com
""")
    # Add index as a property for convenience
    repo.index = Index()
    return repo


@pytest.fixture
def sample_blob():
    """Create a sample blob object."""
    return Blob(b"Hello, World!\n")


@pytest.fixture
def sample_tree(repo, sample_blob):
    """Create a sample tree with one blob."""
    blob_hash = repo.write_object(sample_blob)
    tree = Tree()
    tree.add_entry('100644', 'blob', blob_hash, 'test.txt')
    return tree


@pytest.fixture
def sample_commit(sample_tree, repo):
    """Sample commit object."""
    tree_hash = repo.write_object(sample_tree)
    commit = Commit.create(
        tree_hash=tree_hash,
        parent_hashes=[],
        author="Test User <test@example.com>",
        committer="Test User <test@example.com>",
        message="Test commit"
    )
    return commit


@pytest.fixture
def repo_with_commits(repo_with_config):
    """Repository with a couple of commits."""
    repo = repo_with_config
    index = Index()
    
    # First commit
    file1 = repo.work_tree / "file1.txt"
    file1.write_text("Hello, World!")
    # Use pathlib object directly to avoid symlink resolution issues
    index.add_file(repo_with_config, file1)
    
    # Create first commit
    tree_hash1 = build_tree_from_index(repo, index)
    commit1 = Commit.create(
        tree_hash=tree_hash1,
        parent_hashes=[],
        author="Test User <test@example.com>",
        committer="Test User <test@example.com>",
        message="First commit"
    )
    commit_hash1 = repo.write_object(commit1)
    repo.head_file.write_text(commit_hash1 + "\n")
    
    # Second commit
    file2 = repo.work_tree / "file2.txt"
    file2.write_text("Second file")
    # Use pathlib object directly
    index.add_file(repo_with_config, file2)
    
    tree_hash2 = build_tree_from_index(repo, index)
    commit2 = Commit.create(
        tree_hash=tree_hash2,
        parent_hashes=[commit_hash1],
        author="Test User <test@example.com>",
        committer="Test User <test@example.com>",
        message="Second commit"
    )
    commit_hash2 = repo.write_object(commit2)
    repo.head_file.write_text(commit_hash2 + "\n")
    
    # Update repo.index to have current state (already written to disk by add_file)
    repo.index = index
    
    return repo


@pytest.fixture
def working_files(repo):
    """Create sample file structure in repository."""
    # Create files
    file1 = repo.work_tree / "test1.txt"
    file2 = repo.work_tree / "test2.txt"
    
    # Create nested directory
    (repo.work_tree / "subdir").mkdir()
    file3 = repo.work_tree / "subdir" / "test3.txt"
    
    file1.write_text("Content 1")
    file2.write_text("Content 2")
    file3.write_text("Content 3")
    
    return {
        'file1': file1,
        'file2': file2,
        'file3': file3
    }


def make_commit(repo, message="Test commit"):
    """
    Helper function to create a commit from current index state.
    
    Args:
        repo: Repository instance (must have index attribute)
        message: Commit message
        
    Returns:
        str: Commit hash, or None if no changes
    """
    # Use repo.index if it exists, otherwise create new one
    if hasattr(repo, 'index') and repo.index:
        index = repo.index
    else:
        index = Index()
    
    # Check if index has entries
    if not index.entries:
        return None
    
    # Build tree from index
    tree_hash = build_tree_from_index(repo, index)
    
    # Get parent commit
    parent_hashes = []
    head_hash = repo.refs.resolve_head()
    if head_hash:
        parent_hashes = [head_hash]
    
    # Create commit
    commit = Commit.create(
        tree_hash=tree_hash,
        parent_hashes=parent_hashes,
        author="Test User <test@example.com>",
        committer="Test User <test@example.com>",
        message=message
    )
    
    # Write commit and update HEAD
    commit_hash = repo.write_object(commit)
    repo.head_file.write_text(commit_hash + "\n")
    
    return commit_hash
