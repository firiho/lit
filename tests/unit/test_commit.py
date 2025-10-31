"""Commit object tests."""

import pytest
import time
from lit.core.objects import Commit
from lit.core.repository import Repository
import tempfile
import shutil


def test_commit_creation():
    """Test creating empty commit."""
    commit = Commit()
    assert commit.type == 'commit'
    assert commit.tree == ''
    assert len(commit.parents) == 0
    assert commit.message == ''


def test_commit_create_with_defaults():
    """Test creating commit with create() method."""
    commit = Commit.create(
        tree_hash='a' * 40,
        parent_hashes=[],
        author='John Doe <john@example.com>',
        committer='John Doe <john@example.com>',
        message='Initial commit'
    )
    
    assert commit.tree == 'a' * 40
    assert len(commit.parents) == 0
    assert commit.author == 'John Doe <john@example.com>'
    assert commit.committer == 'John Doe <john@example.com>'
    assert commit.message == 'Initial commit'
    assert commit.author_time > 0
    assert commit.author_timezone == '+0000'


def test_commit_create_with_parent():
    """Test creating commit with parent."""
    commit = Commit.create(
        tree_hash='a' * 40,
        parent_hashes=['b' * 40],
        author='Jane Doe <jane@example.com>',
        committer='Jane Doe <jane@example.com>',
        message='Second commit'
    )
    
    assert len(commit.parents) == 1
    assert commit.parents[0] == 'b' * 40


def test_commit_create_with_timestamp():
    """Test creating commit with specific timestamp."""
    timestamp = 1698660000
    commit = Commit.create(
        tree_hash='a' * 40,
        parent_hashes=[],
        author='Test User <test@example.com>',
        committer='Test User <test@example.com>',
        message='Test commit',
        timestamp=timestamp,
        timezone='-0500'
    )
    
    assert commit.author_time == timestamp
    assert commit.committer_time == timestamp
    assert commit.author_timezone == '-0500'
    assert commit.committer_timezone == '-0500'


def test_commit_serialize():
    """Test commit serialization."""
    commit = Commit.create(
        tree_hash='a' * 40,
        parent_hashes=['b' * 40],
        author='John Doe <john@example.com>',
        committer='John Doe <john@example.com>',
        message='Test message',
        timestamp=1698660000
    )
    
    serialized = commit.serialize()
    content = serialized.decode()
    
    assert 'tree ' + 'a' * 40 in content
    assert 'parent ' + 'b' * 40 in content
    assert 'author John Doe <john@example.com> 1698660000 +0000' in content
    assert 'committer John Doe <john@example.com> 1698660000 +0000' in content
    assert 'Test message' in content


def test_commit_roundtrip():
    """Test commit serialize/deserialize cycle."""
    commit1 = Commit.create(
        tree_hash='a' * 40,
        parent_hashes=['b' * 40, 'c' * 40],
        author='Alice <alice@example.com>',
        committer='Bob <bob@example.com>',
        message='Multi-line\ncommit\nmessage',
        timestamp=1698660000,
        timezone='-0800'
    )
    
    serialized = commit1.serialize()
    
    commit2 = Commit()
    commit2.deserialize(serialized)
    
    assert commit2.tree == 'a' * 40
    assert len(commit2.parents) == 2
    assert commit2.parents[0] == 'b' * 40
    assert commit2.parents[1] == 'c' * 40
    assert commit2.author == 'Alice <alice@example.com>'
    assert commit2.committer == 'Bob <bob@example.com>'
    assert commit2.author_time == 1698660000
    assert commit2.author_timezone == '-0800'
    assert commit2.message == 'Multi-line\ncommit\nmessage'


def test_commit_hash():
    """Test commit hash computation."""
    commit = Commit.create(
        tree_hash='a' * 40,
        parent_hashes=[],
        author='Test <test@example.com>',
        committer='Test <test@example.com>',
        message='Test',
        timestamp=1698660000
    )
    
    hash_value = commit.compute_hash()
    assert len(hash_value) == 40
    assert isinstance(hash_value, str)


def test_commit_hash_deterministic():
    """Test commit hash is deterministic."""
    commit1 = Commit.create(
        tree_hash='a' * 40,
        parent_hashes=[],
        author='Test <test@example.com>',
        committer='Test <test@example.com>',
        message='Same commit',
        timestamp=1698660000
    )
    
    commit2 = Commit.create(
        tree_hash='a' * 40,
        parent_hashes=[],
        author='Test <test@example.com>',
        committer='Test <test@example.com>',
        message='Same commit',
        timestamp=1698660000
    )
    
    assert commit1.compute_hash() == commit2.compute_hash()


def test_commit_different_message_different_hash():
    """Test different messages produce different hashes."""
    commit1 = Commit.create(
        tree_hash='a' * 40,
        parent_hashes=[],
        author='Test <test@example.com>',
        committer='Test <test@example.com>',
        message='First message',
        timestamp=1698660000
    )
    
    commit2 = Commit.create(
        tree_hash='a' * 40,
        parent_hashes=[],
        author='Test <test@example.com>',
        committer='Test <test@example.com>',
        message='Second message',
        timestamp=1698660000
    )
    
    assert commit1.compute_hash() != commit2.compute_hash()


@pytest.fixture
def temp_repo():
    """Create temporary repository."""
    temp_dir = tempfile.mkdtemp()
    repo = Repository(temp_dir)
    repo.init()
    yield repo
    shutil.rmtree(temp_dir)


def test_commit_write_and_read(temp_repo):
    """Test writing and reading commit from repository."""
    commit1 = Commit.create(
        tree_hash='a' * 40,
        parent_hashes=['b' * 40],
        author='Test User <test@example.com>',
        committer='Test User <test@example.com>',
        message='Test commit for storage',
        timestamp=1698660000
    )
    
    hash_value = temp_repo.write_object(commit1)
    
    commit2 = temp_repo.read_object(hash_value)
    assert isinstance(commit2, Commit)
    assert commit2.tree == 'a' * 40
    assert commit2.parents[0] == 'b' * 40
    assert commit2.message == 'Test commit for storage'


def test_commit_no_parents():
    """Test initial commit with no parents."""
    commit = Commit.create(
        tree_hash='a' * 40,
        parent_hashes=[],
        author='First <first@example.com>',
        committer='First <first@example.com>',
        message='Initial commit'
    )
    
    serialized = commit.serialize().decode()
    assert 'parent' not in serialized
    assert 'tree ' in serialized


def test_commit_multiple_parents():
    """Test merge commit with multiple parents."""
    commit = Commit.create(
        tree_hash='a' * 40,
        parent_hashes=['b' * 40, 'c' * 40, 'd' * 40],
        author='Merger <merge@example.com>',
        committer='Merger <merge@example.com>',
        message='Merge commit'
    )
    
    assert len(commit.parents) == 3
    serialized = commit.serialize().decode()
    assert serialized.count('parent') == 3


def test_commit_repr():
    """Test commit string representation."""
    commit = Commit.create(
        tree_hash='a' * 40,
        parent_hashes=['b' * 40],
        author='Test <test@example.com>',
        committer='Test <test@example.com>',
        message='Short message'
    )
    
    repr_str = repr(commit)
    assert 'Commit' in repr_str
    assert 'parents=1' in repr_str
    assert 'Short message' in repr_str
