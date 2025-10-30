"""Repository initialization tests."""

import pytest
import tempfile
import shutil
from pathlib import Path
from lit.core.repository import Repository
from lit.core.objects import Blob


@pytest.fixture
def temp_repo():
    """Create temporary repository for testing."""
    temp_dir = tempfile.mkdtemp()
    repo = Repository(temp_dir)
    yield repo
    shutil.rmtree(temp_dir)


def test_repository_init(temp_repo):
    """Test repository initialization creates structure."""
    temp_repo.init()
    assert temp_repo.lit_dir.exists()
    assert temp_repo.objects_dir.exists()
    assert temp_repo.refs_dir.exists()
    assert temp_repo.heads_dir.exists()
    assert temp_repo.head_file.exists()
    assert temp_repo.config_file.exists()


def test_repository_head_content(temp_repo):
    """Test HEAD points to main branch."""
    temp_repo.init()
    head_content = temp_repo.head_file.read_text()
    assert head_content == 'ref: refs/heads/main\n'


def test_repository_config_content(temp_repo):
    """Test config file contains version."""
    temp_repo.init()
    config_content = temp_repo.config_file.read_text()
    assert 'repositoryformatversion' in config_content


def test_repository_already_exists(temp_repo):
    """Test duplicate init raises error."""
    temp_repo.init()
    with pytest.raises(Exception, match="already exists"):
        temp_repo.init()


def test_write_and_read_blob(temp_repo):
    """Test blob storage and retrieval."""
    temp_repo.init()
    blob = Blob(b'test data')
    hash_value = temp_repo.write_object(blob)
    
    read_blob = temp_repo.read_object(hash_value)
    assert isinstance(read_blob, Blob)
    assert read_blob.data == b'test data'


def test_write_blob_creates_subdirectory(temp_repo):
    """Test object stored in subdirectory."""
    temp_repo.init()
    blob = Blob(b'test')
    hash_value = temp_repo.write_object(blob)
    
    obj_path = temp_repo.object_path(hash_value)
    assert obj_path.exists()
    assert obj_path.parent.name == hash_value[:2]


def test_find_repository_in_subdirectory(temp_repo):
    """Test finding repo from nested directory."""
    temp_repo.init()
    subdir = temp_repo.work_tree / 'subdir' / 'nested'
    subdir.mkdir(parents=True)
    
    found_repo = Repository.find_repository(str(subdir))
    assert found_repo is not None
    assert found_repo.work_tree == temp_repo.work_tree


def test_find_repository_none():
    """Test no repo found returns None."""
    with tempfile.TemporaryDirectory() as temp_dir:
        found_repo = Repository.find_repository(temp_dir)
        assert found_repo is None
