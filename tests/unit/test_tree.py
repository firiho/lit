"""Tree object tests."""

import pytest
import tempfile
import shutil
from pathlib import Path
from lit.core.objects import Tree, TreeEntry, Blob
from lit.core.repository import Repository


def test_tree_entry_creation():
    """Test creating a tree entry."""
    entry = TreeEntry('100644', 'blob', 'a' * 40, 'file.txt')
    assert entry.mode == '100644'
    assert entry.type == 'blob'
    assert entry.hash == 'a' * 40
    assert entry.name == 'file.txt'


def test_tree_entry_sorting():
    """Test tree entries sort by name."""
    entry1 = TreeEntry('100644', 'blob', 'a' * 40, 'zebra.txt')
    entry2 = TreeEntry('100644', 'blob', 'b' * 40, 'apple.txt')
    assert entry2 < entry1


def test_tree_creation():
    """Test creating empty tree."""
    tree = Tree()
    assert len(tree.entries) == 0
    assert tree.type == 'tree'


def test_tree_add_entry():
    """Test adding entry to tree."""
    tree = Tree()
    tree.add_entry('100644', 'blob', 'a' * 40, 'file.txt')
    assert len(tree.entries) == 1
    assert tree.entries[0].name == 'file.txt'


def test_tree_entries_sorted():
    """Test entries are automatically sorted."""
    tree = Tree()
    tree.add_entry('100644', 'blob', 'a' * 40, 'zebra.txt')
    tree.add_entry('100644', 'blob', 'b' * 40, 'apple.txt')
    tree.add_entry('040000', 'tree', 'c' * 40, 'middle')
    
    assert tree.entries[0].name == 'apple.txt'
    assert tree.entries[1].name == 'middle'
    assert tree.entries[2].name == 'zebra.txt'


def test_tree_serialize():
    """Test tree serialization."""
    tree = Tree()
    tree.add_entry('100644', 'blob', 'a' * 40, 'file.txt')
    
    serialized = tree.serialize()
    assert b'100644 file.txt\0' in serialized
    assert len(serialized) > 0


def test_tree_roundtrip():
    """Test tree serialize/deserialize cycle."""
    tree1 = Tree()
    tree1.add_entry('100644', 'blob', 'a' * 40, 'file1.txt')
    tree1.add_entry('100755', 'blob', 'b' * 40, 'script.sh')
    tree1.add_entry('040000', 'tree', 'c' * 40, 'subdir')
    
    serialized = tree1.serialize()
    
    tree2 = Tree()
    tree2.deserialize(serialized)
    
    assert len(tree2.entries) == 3
    assert tree2.entries[0].name == 'file1.txt'
    assert tree2.entries[0].mode == '100644'
    assert tree2.entries[1].name == 'script.sh'
    assert tree2.entries[2].name == 'subdir'
    assert tree2.entries[2].type == 'tree'


def test_tree_hash():
    """Test tree hash computation."""
    tree = Tree()
    tree.add_entry('100644', 'blob', 'a' * 40, 'file.txt')
    
    hash_value = tree.compute_hash()
    assert len(hash_value) == 40
    assert isinstance(hash_value, str)


def test_tree_hash_deterministic():
    """Test tree hash is deterministic."""
    tree1 = Tree()
    tree1.add_entry('100644', 'blob', 'a' * 40, 'file.txt')
    
    tree2 = Tree()
    tree2.add_entry('100644', 'blob', 'a' * 40, 'file.txt')
    
    assert tree1.compute_hash() == tree2.compute_hash()


@pytest.fixture
def temp_dir():
    """Create temporary directory with files."""
    temp = tempfile.mkdtemp()
    temp_path = Path(temp)
    
    (temp_path / 'file1.txt').write_text('content1')
    (temp_path / 'file2.txt').write_text('content2')
    
    subdir = temp_path / 'subdir'
    subdir.mkdir()
    (subdir / 'nested.txt').write_text('nested content')
    
    yield temp
    shutil.rmtree(temp)


@pytest.fixture
def temp_repo():
    """Create temporary repository."""
    temp_dir = tempfile.mkdtemp()
    repo = Repository(temp_dir)
    repo.init()
    yield repo
    shutil.rmtree(temp_dir)


def test_tree_from_directory(temp_dir, temp_repo):
    """Test building tree from directory."""
    tree = Tree.from_directory(temp_repo, temp_dir)
    
    assert len(tree.entries) == 3
    names = [e.name for e in tree.entries]
    assert 'file1.txt' in names
    assert 'file2.txt' in names
    assert 'subdir' in names


def test_tree_from_directory_ignores_hidden(temp_repo):
    """Test tree building ignores hidden files."""
    temp = tempfile.mkdtemp()
    temp_path = Path(temp)
    
    (temp_path / 'visible.txt').write_text('visible')
    (temp_path / '.hidden').write_text('hidden')
    
    try:
        tree = Tree.from_directory(temp_repo, temp)
        names = [e.name for e in tree.entries]
        assert 'visible.txt' in names
        assert '.hidden' not in names
    finally:
        shutil.rmtree(temp)


def test_tree_write_and_read(temp_repo):
    """Test writing and reading tree from repository."""
    tree1 = Tree()
    tree1.add_entry('100644', 'blob', 'a' * 40, 'file.txt')
    tree1.add_entry('040000', 'tree', 'b' * 40, 'dir')
    
    hash_value = temp_repo.write_object(tree1)
    
    tree2 = temp_repo.read_object(hash_value)
    assert isinstance(tree2, Tree)
    assert len(tree2.entries) == 2
    assert tree2.entries[0].name == 'dir'
    assert tree2.entries[1].name == 'file.txt'
