"""Integration tests for repository initialization and basic operations."""

import pytest
from pathlib import Path
from lit.core.repository import Repository


def test_init_creates_lit_directory(temp_dir):
    """Test that init creates .lit directory structure."""
    repo = Repository(temp_dir)
    repo.init()
    
    assert (temp_dir / '.lit').exists()
    assert (temp_dir / '.lit' / 'objects').exists()
    assert (temp_dir / '.lit' / 'refs' / 'heads').exists()
    assert (temp_dir / '.lit' / 'refs' / 'tags').exists()
    assert (temp_dir / '.lit' / 'HEAD').exists()


def test_init_creates_head_file(temp_dir):
    """Test that init creates HEAD file pointing to main."""
    repo = Repository(temp_dir)
    repo.init()
    
    head_content = (temp_dir / '.lit' / 'HEAD').read_text()
    assert head_content.strip() == 'ref: refs/heads/main'


def test_init_creates_config_file(temp_dir):
    """Test that init creates config file."""
    repo = Repository(temp_dir)
    repo.init()
    
    assert (temp_dir / '.lit' / 'config').exists()


def test_double_init_fails(temp_dir):
    """Test that initializing twice fails."""
    repo = Repository(temp_dir)
    repo.init()  # First init succeeds
    
    # Second init should raise exception
    with pytest.raises(Exception):
        repo.init()


def test_repo_detects_existing_lit(temp_dir):
    """Test that Repository detects existing .lit directory."""
    # Initialize
    repo1 = Repository(temp_dir)
    repo1.init()
    
    # Create new repo object for same directory
    repo2 = Repository(temp_dir)
    assert repo2.lit_dir.exists() is True


def test_config_roundtrip(temp_dir):
    """Test setting and getting config values."""
    import configparser
    
    repo = Repository(temp_dir)
    repo.init()
    
    # Set config
    config = configparser.ConfigParser()
    if not config.has_section('user'):
        config.add_section('user')
    config.set("user", "name", "Test User")
    config.set("user", "email", "test@example.com")
    
    with open(repo.config_file, 'w') as f:
        config.write(f)
    
    # Get config
    config2 = configparser.ConfigParser()
    config2.read(repo.config_file)
    assert config2.get("user", "name") == "Test User"
    assert config2.get("user", "email") == "test@example.com"


def test_config_persists_across_instances(temp_dir):
    """Test that config persists when reopening repository."""
    import configparser
    
    # First instance
    repo1 = Repository(temp_dir)
    repo1.init()
    
    config = configparser.ConfigParser()
    if not config.has_section('user'):
        config.add_section('user')
    config.set("user", "name", "Test User")
    
    with open(repo1.config_file, 'w') as f:
        config.write(f)
    
    # Second instance
    repo2 = Repository(temp_dir)
    config2 = configparser.ConfigParser()
    config2.read(repo2.config_file)
    assert config2.get("user", "name") == "Test User"
