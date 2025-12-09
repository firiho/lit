"""Integration tests for cherry-pick command."""

import pytest
import os
from pathlib import Path
from click.testing import CliRunner

from lit.cli.main import cli


@pytest.fixture
def runner():
    """Create CLI runner."""
    return CliRunner()


@pytest.fixture
def repo_with_branches(runner, tmp_path):
    """Create a repository with multiple branches and commits."""
    os.chdir(tmp_path)
    
    # Initialize repo
    result = runner.invoke(cli, ['init'])
    assert result.exit_code == 0
    
    # Configure user
    runner.invoke(cli, ['config', 'set', 'user.name', 'Test User'])
    runner.invoke(cli, ['config', 'set', 'user.email', 'test@test.com'])
    
    # Create initial commit on main
    Path('file.txt').write_text('initial content\n')
    runner.invoke(cli, ['add', 'file.txt'])
    runner.invoke(cli, ['commit', '-m', 'Initial commit'])
    
    # Create feature branch
    runner.invoke(cli, ['branch', 'feature'])
    
    # Add commit on main
    Path('file.txt').write_text('initial content\nmain line\n')
    runner.invoke(cli, ['add', 'file.txt'])
    result = runner.invoke(cli, ['commit', '-m', 'Add main line'])
    
    # Extract commit hash
    main_commit = None
    for line in result.output.split('\n'):
        if 'Created commit' in line:
            main_commit = line.split()[-1]
            break
    
    # Switch to feature branch and make different changes
    runner.invoke(cli, ['checkout', 'feature'])
    Path('feature.txt').write_text('feature content\n')
    runner.invoke(cli, ['add', 'feature.txt'])
    runner.invoke(cli, ['commit', '-m', 'Add feature file'])
    
    return {'path': tmp_path, 'main_commit': main_commit}


class TestCherryPickBasic:
    """Tests for basic cherry-pick functionality."""
    
    def test_cherry_pick_commit(self, runner, repo_with_branches):
        """Test cherry-picking a commit."""
        main_commit = repo_with_branches['main_commit']
        
        result = runner.invoke(cli, ['cherry-pick', main_commit])
        assert result.exit_code == 0
        assert 'Cherry-picked' in result.output
        assert 'Add main line' in result.output
    
    def test_cherry_pick_creates_new_commit(self, runner, repo_with_branches):
        """Test that cherry-pick creates a new commit with different hash."""
        main_commit = repo_with_branches['main_commit']
        
        # Get current HEAD before
        result = runner.invoke(cli, ['log', '--oneline'])
        commits_before = len(result.output.strip().split('\n'))
        
        runner.invoke(cli, ['cherry-pick', main_commit])
        
        # Check we have one more commit
        result = runner.invoke(cli, ['log', '--oneline'])
        commits_after = len(result.output.strip().split('\n'))
        
        assert commits_after == commits_before + 1
    
    def test_cherry_pick_preserves_message(self, runner, repo_with_branches):
        """Test that cherry-pick preserves original commit message."""
        main_commit = repo_with_branches['main_commit']
        
        runner.invoke(cli, ['cherry-pick', main_commit])
        
        result = runner.invoke(cli, ['log', '--oneline'])
        assert 'Add main line' in result.output


class TestCherryPickWithOptions:
    """Tests for cherry-pick options."""
    
    def test_cherry_pick_custom_message(self, runner, repo_with_branches):
        """Test cherry-pick with custom message."""
        main_commit = repo_with_branches['main_commit']
        
        runner.invoke(cli, ['cherry-pick', main_commit, '-m', 'Custom cherry-pick message'])
        
        result = runner.invoke(cli, ['log', '--oneline'])
        assert 'Custom cherry-pick message' in result.output
    
    def test_cherry_pick_no_commit(self, runner, repo_with_branches):
        """Test cherry-pick with --no-commit."""
        main_commit = repo_with_branches['main_commit']
        
        # Get current HEAD before
        result = runner.invoke(cli, ['log', '--oneline'])
        commits_before = len(result.output.strip().split('\n'))
        
        result = runner.invoke(cli, ['cherry-pick', main_commit, '--no-commit'])
        assert result.exit_code == 0
        assert 'Changes applied' in result.output
        
        # Commit count should not change
        result = runner.invoke(cli, ['log', '--oneline'])
        commits_after = len(result.output.strip().split('\n'))
        
        assert commits_after == commits_before


class TestCherryPickRefs:
    """Tests for cherry-pick with different ref formats."""
    
    def test_cherry_pick_head_tilde(self, runner, tmp_path):
        """Test cherry-pick with HEAD~N syntax."""
        os.chdir(tmp_path)
        
        runner.invoke(cli, ['init'])
        runner.invoke(cli, ['config', 'set', 'user.name', 'Test'])
        runner.invoke(cli, ['config', 'set', 'user.email', 'test@test.com'])
        
        # Create base commit
        Path('file.txt').write_text('base\n')
        runner.invoke(cli, ['add', 'file.txt'])
        runner.invoke(cli, ['commit', '-m', 'Base'])
        
        # Create second commit
        Path('file.txt').write_text('base\nsecond\n')
        runner.invoke(cli, ['add', 'file.txt'])
        runner.invoke(cli, ['commit', '-m', 'Second'])
        
        # Create third commit
        Path('file.txt').write_text('base\nsecond\nthird\n')
        runner.invoke(cli, ['add', 'file.txt'])
        runner.invoke(cli, ['commit', '-m', 'Third'])
        
        # Create branch from base
        runner.invoke(cli, ['branch', 'test', 'HEAD~2'])
        runner.invoke(cli, ['checkout', 'test'])
        
        # Cherry-pick second commit
        result = runner.invoke(cli, ['cherry-pick', 'main~1'])
        # This may fail due to conflict, but the ref should resolve
        assert 'Unknown commit' not in result.output


class TestCherryPickAbort:
    """Tests for cherry-pick --abort."""
    
    def test_abort_no_cherry_pick(self, runner, repo_with_branches):
        """Test abort when no cherry-pick in progress."""
        result = runner.invoke(cli, ['cherry-pick', '--abort'])
        assert 'No cherry-pick in progress' in result.output


class TestCherryPickErrors:
    """Tests for cherry-pick error handling."""
    
    def test_cherry_pick_invalid_commit(self, runner, repo_with_branches):
        """Test cherry-pick with invalid commit."""
        result = runner.invoke(cli, ['cherry-pick', 'nonexistent'])
        assert 'Unknown commit' in result.output
    
    def test_cherry_pick_no_commit_specified(self, runner, repo_with_branches):
        """Test cherry-pick without commit argument."""
        result = runner.invoke(cli, ['cherry-pick'])
        assert 'No commit specified' in result.output


class TestCherryPickHelp:
    """Tests for cherry-pick help."""
    
    def test_cherry_pick_help(self, runner):
        """Test cherry-pick --help."""
        result = runner.invoke(cli, ['cherry-pick', '--help'])
        assert result.exit_code == 0
        assert 'Apply changes from a specific commit' in result.output
        assert '--continue' in result.output
        assert '--abort' in result.output
        assert '--no-commit' in result.output
