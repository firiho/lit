"""Index tests."""

import pytest
import tempfile
import shutil
from pathlib import Path
from lit.core.index import Index, IndexEntry
from lit.core.repository import Repository


def test_index_entry_creation():
    """Test creating index entry."""
    entry = IndexEntry(
        ctime=1000, ctime_ns=0,
        mtime=2000, mtime_ns=0,
        dev=1, ino=2, mode=0o100644,
        uid=1000, gid=1000, size=100,
        sha1='a' * 40, flags=8,
        path='file.txt'
    )
    
    assert entry.path == 'file.txt'
    assert entry.sha1 == 'a' * 40
    assert entry.mode == 0o100644


def test_index_creation():
    """Test creating empty index."""
    index = Index()
    assert len(index) == 0
    assert index.version == 2


def test_index_add_entry():
    """Test adding entry to index."""
    index = Index()
    index.add_entry(
        path='test.txt',
        sha1='a' * 40,
        mode=0o100644,
        size=100
    )
    
    assert len(index) == 1
    assert 'test.txt' in index.entries
    entry = index.get_entry('test.txt')
    assert entry.sha1 == 'a' * 40


def test_index_add_multiple_entries():
    """Test adding multiple entries."""
    index = Index()
    index.add_entry('file1.txt', 'a' * 40, 0o100644, 10)
    index.add_entry('file2.txt', 'b' * 40, 0o100644, 20)
    index.add_entry('dir/file3.txt', 'c' * 40, 0o100644, 30)
    
    assert len(index) == 3
    assert index.get_entry('file1.txt').sha1 == 'a' * 40
    assert index.get_entry('file2.txt').sha1 == 'b' * 40
    assert index.get_entry('dir/file3.txt').sha1 == 'c' * 40


def test_index_remove_entry():
    """Test removing entry from index."""
    index = Index()
    index.add_entry('test.txt', 'a' * 40, 0o100644, 100)
    assert len(index) == 1
    
    index.remove_entry('test.txt')
    assert len(index) == 0
    assert index.get_entry('test.txt') is None


def test_index_clear():
    """Test clearing index."""
    index = Index()
    index.add_entry('file1.txt', 'a' * 40, 0o100644, 10)
    index.add_entry('file2.txt', 'b' * 40, 0o100644, 20)
    assert len(index) == 2
    
    index.clear()
    assert len(index) == 0


@pytest.fixture
def temp_repo():
    """Create temporary repository."""
    temp_dir = tempfile.mkdtemp()
    repo = Repository(temp_dir)
    repo.init()
    yield repo
    shutil.rmtree(temp_dir)


def test_index_add_file(temp_repo):
    """Test staging a file."""
    test_file = temp_repo.work_tree / 'test.txt'
    test_file.write_text('Hello, Lit!')
    
    index = Index()
    sha1 = index.add_file(temp_repo, 'test.txt')
    
    assert len(index) == 1
    assert len(sha1) == 40
    entry = index.get_entry('test.txt')
    assert entry.sha1 == sha1
    assert entry.path == 'test.txt'


def test_index_add_file_absolute_path(temp_repo):
    """Test staging file with absolute path."""
    test_file = temp_repo.work_tree / 'absolute.txt'
    test_file.write_text('Absolute path test')
    
    index = Index()
    sha1 = index.add_file(temp_repo, str(test_file))
    
    assert len(index) == 1
    entry = index.get_entry('absolute.txt')
    assert entry is not None


def test_index_add_nonexistent_file(temp_repo):
    """Test staging nonexistent file raises error."""
    index = Index()
    
    with pytest.raises(FileNotFoundError):
        index.add_file(temp_repo, 'nonexistent.txt')


def test_index_write_and_read(temp_repo):
    """Test writing and reading index."""
    index1 = Index()
    index1.add_entry('file1.txt', 'a' * 40, 0o100644, 100, mtime=1000)
    index1.add_entry('file2.txt', 'b' * 40, 0o100755, 200, mtime=2000)
    
    index_path = temp_repo.index_file
    index1.write(str(index_path))
    
    index2 = Index()
    index2.read(str(index_path))
    
    assert len(index2) == 2
    assert index2.get_entry('file1.txt').sha1 == 'a' * 40
    assert index2.get_entry('file2.txt').sha1 == 'b' * 40
    assert index2.get_entry('file1.txt').mode == 0o100644
    assert index2.get_entry('file2.txt').mode == 0o100755


def test_index_roundtrip_with_real_file(temp_repo):
    """Test full roundtrip with real file."""
    test_file = temp_repo.work_tree / 'roundtrip.txt'
    test_file.write_text('Roundtrip test content')
    
    index1 = Index()
    sha1 = index1.add_file(temp_repo, 'roundtrip.txt')
    
    index_path = temp_repo.index_file
    index1.write(str(index_path))
    
    index2 = Index()
    index2.read(str(index_path))
    
    assert len(index2) == 1
    entry = index2.get_entry('roundtrip.txt')
    assert entry.sha1 == sha1
    assert entry.path == 'roundtrip.txt'


def test_index_read_nonexistent():
    """Test reading nonexistent index returns empty."""
    index = Index()
    index.read('/nonexistent/index')
    assert len(index) == 0


def test_index_sorted_entries(temp_repo):
    """Test entries are sorted when written."""
    index = Index()
    index.add_entry('zebra.txt', 'a' * 40, 0o100644, 10)
    index.add_entry('apple.txt', 'b' * 40, 0o100644, 20)
    index.add_entry('middle.txt', 'c' * 40, 0o100644, 30)
    
    index_path = temp_repo.index_file
    index.write(str(index_path))
    
    index2 = Index()
    index2.read(str(index_path))
    
    paths = list(index2.entries.keys())
    assert paths == ['apple.txt', 'middle.txt', 'zebra.txt']


def test_index_multiple_files(temp_repo):
    """Test staging multiple files."""
    (temp_repo.work_tree / 'file1.txt').write_text('Content 1')
    (temp_repo.work_tree / 'file2.txt').write_text('Content 2')
    (temp_repo.work_tree / 'file3.txt').write_text('Content 3')
    
    index = Index()
    index.add_file(temp_repo, 'file1.txt')
    index.add_file(temp_repo, 'file2.txt')
    index.add_file(temp_repo, 'file3.txt')
    
    assert len(index) == 3
    assert index.get_entry('file1.txt') is not None
    assert index.get_entry('file2.txt') is not None
    assert index.get_entry('file3.txt') is not None


def test_index_update_existing_entry():
    """Test updating existing entry."""
    index = Index()
    index.add_entry('test.txt', 'a' * 40, 0o100644, 100)
    
    assert index.get_entry('test.txt').sha1 == 'a' * 40
    
    index.add_entry('test.txt', 'b' * 40, 0o100644, 200)
    
    assert len(index) == 1
    assert index.get_entry('test.txt').sha1 == 'b' * 40
    assert index.get_entry('test.txt').size == 200


def test_index_repr():
    """Test index string representation."""
    index = Index()
    assert 'Index' in repr(index)
    assert 'entries=0' in repr(index)
    
    index.add_entry('test.txt', 'a' * 40, 0o100644, 100)
    assert 'entries=1' in repr(index)
