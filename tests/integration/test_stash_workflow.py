"""Integration tests for stash command."""

import pytest
import os
from pathlib import Path
from click.testing import CliRunner

from lit.cli.main import cli
from lit.core.repository import Repository


@pytest.fixture
def runner():
    """Create CLI runner."""
    return CliRunner()


@pytest.fixture
def initialized_repo(runner, tmp_path):
    """Create a repository with initial commit."""
    os.chdir(tmp_path)
    
    # Initialize repo
    result = runner.invoke(cli, ['init'])
    assert result.exit_code == 0
    
    # Configure user
    runner.invoke(cli, ['config', 'set', 'user.name', 'Test User'])
    runner.invoke(cli, ['config', 'set', 'user.email', 'test@test.com'])
    
    # Create and commit initial file
    Path('file.txt').write_text('initial content')
    runner.invoke(cli, ['add', 'file.txt'])
    runner.invoke(cli, ['commit', '-m', 'Initial commit'])
    
    return tmp_path


class TestStashPush:
    """Tests for lit stash push."""
    
    def test_stash_modified_file(self, runner, initialized_repo):
        """Test stashing a modified file."""
        # Modify file
        Path('file.txt').write_text('modified content')
        
        # Stash changes
        result = runner.invoke(cli, ['stash', 'push', '-m', 'My stash'])
        assert result.exit_code == 0
        assert 'Saved working directory' in result.output
        
        # File should be reset
        assert Path('file.txt').read_text() == 'initial content'
    
    def test_stash_with_message(self, runner, initialized_repo):
        """Test stashing with custom message."""
        Path('file.txt').write_text('changed')
        
        result = runner.invoke(cli, ['stash', 'push', '-m', 'Custom message'])
        assert result.exit_code == 0
        assert 'Custom message' in result.output
    
    def test_stash_nothing_to_stash(self, runner, initialized_repo):
        """Test stash when no changes."""
        result = runner.invoke(cli, ['stash', 'push'])
        assert result.exit_code == 0
        assert 'No local changes' in result.output


class TestStashList:
    """Tests for lit stash list."""
    
    def test_list_empty(self, runner, initialized_repo):
        """Test listing when no stashes."""
        result = runner.invoke(cli, ['stash', 'list'])
        assert result.exit_code == 0
        assert 'No stashed changes' in result.output
    
    def test_list_multiple_stashes(self, runner, initialized_repo):
        """Test listing multiple stashes."""
        # Create two stashes
        Path('file.txt').write_text('change 1')
        runner.invoke(cli, ['stash', 'push', '-m', 'First stash'])
        
        Path('file.txt').write_text('change 2')
        runner.invoke(cli, ['stash', 'push', '-m', 'Second stash'])
        
        result = runner.invoke(cli, ['stash', 'list'])
        assert result.exit_code == 0
        assert 'stash@{0}' in result.output
        assert 'Second stash' in result.output
        assert 'stash@{1}' in result.output
        assert 'First stash' in result.output


class TestStashPop:
    """Tests for lit stash pop."""
    
    def test_pop_restores_changes(self, runner, initialized_repo):
        """Test that pop restores changes."""
        Path('file.txt').write_text('stashed content')
        runner.invoke(cli, ['stash', 'push', '-m', 'Test'])
        
        result = runner.invoke(cli, ['stash', 'pop'])
        assert result.exit_code == 0
        assert 'Applied stash@{0}' in result.output
        assert Path('file.txt').read_text() == 'stashed content'
    
    def test_pop_removes_stash(self, runner, initialized_repo):
        """Test that pop removes the stash."""
        Path('file.txt').write_text('content')
        runner.invoke(cli, ['stash', 'push', '-m', 'Test'])
        runner.invoke(cli, ['stash', 'pop'])
        
        result = runner.invoke(cli, ['stash', 'list'])
        assert 'No stashed changes' in result.output
    
    def test_pop_invalid_index(self, runner, initialized_repo):
        """Test pop with invalid index."""
        result = runner.invoke(cli, ['stash', 'pop', '99'])
        assert result.exit_code == 0
        assert 'does not exist' in result.output


class TestStashApply:
    """Tests for lit stash apply."""
    
    def test_apply_restores_changes(self, runner, initialized_repo):
        """Test that apply restores changes."""
        Path('file.txt').write_text('applied content')
        runner.invoke(cli, ['stash', 'push', '-m', 'Test'])
        
        result = runner.invoke(cli, ['stash', 'apply'])
        assert result.exit_code == 0
        assert 'Applied stash@{0}' in result.output
        assert Path('file.txt').read_text() == 'applied content'
    
    def test_apply_keeps_stash(self, runner, initialized_repo):
        """Test that apply keeps the stash."""
        Path('file.txt').write_text('content')
        runner.invoke(cli, ['stash', 'push', '-m', 'Preserved'])
        runner.invoke(cli, ['stash', 'apply'])
        
        result = runner.invoke(cli, ['stash', 'list'])
        assert 'Preserved' in result.output


class TestStashDrop:
    """Tests for lit stash drop."""
    
    def test_drop_removes_stash(self, runner, initialized_repo):
        """Test that drop removes stash without applying."""
        Path('file.txt').write_text('to drop')
        runner.invoke(cli, ['stash', 'push', '-m', 'Drop me'])
        
        result = runner.invoke(cli, ['stash', 'drop'])
        assert result.exit_code == 0
        assert 'Dropped stash@{0}' in result.output
        
        # File should still be initial
        assert Path('file.txt').read_text() == 'initial content'
    
    def test_drop_specific_index(self, runner, initialized_repo):
        """Test dropping a specific stash."""
        Path('file.txt').write_text('first')
        runner.invoke(cli, ['stash', 'push', '-m', 'First'])
        
        Path('file.txt').write_text('second')
        runner.invoke(cli, ['stash', 'push', '-m', 'Second'])
        
        # Drop the second one (index 1)
        result = runner.invoke(cli, ['stash', 'drop', '1'])
        assert result.exit_code == 0
        assert 'First' in result.output
        
        # Second should still exist
        result = runner.invoke(cli, ['stash', 'list'])
        assert 'Second' in result.output


class TestStashShow:
    """Tests for lit stash show."""
    
    def test_show_stash_details(self, runner, initialized_repo):
        """Test showing stash details."""
        Path('file.txt').write_text('show me')
        runner.invoke(cli, ['stash', 'push', '-m', 'Show test'])
        
        result = runner.invoke(cli, ['stash', 'show', '0'])
        assert result.exit_code == 0
        assert 'Show test' in result.output
        assert 'Branch:' in result.output
        assert 'file.txt' in result.output
    
    def test_show_invalid_index(self, runner, initialized_repo):
        """Test showing invalid stash."""
        result = runner.invoke(cli, ['stash', 'show', '5'])
        assert 'does not exist' in result.output


class TestStashRefParsing:
    """Tests for stash reference parsing."""
    
    def test_numeric_ref(self, runner, initialized_repo):
        """Test numeric stash reference."""
        Path('file.txt').write_text('test')
        runner.invoke(cli, ['stash', 'push', '-m', 'Test'])
        
        result = runner.invoke(cli, ['stash', 'pop', '0'])
        assert result.exit_code == 0
    
    def test_stash_at_ref(self, runner, initialized_repo):
        """Test stash@{N} format."""
        Path('file.txt').write_text('test')
        runner.invoke(cli, ['stash', 'push', '-m', 'Test'])
        
        result = runner.invoke(cli, ['stash', 'show', 'stash@{0}'])
        assert result.exit_code == 0
        assert 'Test' in result.output


class TestStashDefault:
    """Tests for default stash behavior."""
    
    def test_stash_without_subcommand(self, runner, initialized_repo):
        """Test 'lit stash' defaults to push."""
        Path('file.txt').write_text('default test')
        
        result = runner.invoke(cli, ['stash'])
        assert result.exit_code == 0
        assert 'Saved working directory' in result.output


class TestStashHelp:
    """Tests for stash help."""
    
    def test_stash_help(self, runner):
        """Test stash --help."""
        result = runner.invoke(cli, ['stash', '--help'])
        assert result.exit_code == 0
        assert 'Stash changes' in result.output
        assert 'push' in result.output
        assert 'pop' in result.output
        assert 'list' in result.output
