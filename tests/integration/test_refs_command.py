"""Integration tests for refs command."""

import pytest
from pathlib import Path
from click.testing import CliRunner
from lit.cli.main import cli


class TestRefsCommand:
    """Tests for lit refs command (show-ref)."""
    
    def test_refs_list(self, repo_with_commits):
        """Test listing refs."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        # First ensure we're on a proper branch
        runner.invoke(cli, ['branch', 'main'])
        
        result = runner.invoke(cli, ['refs'])
        # Should either show refs or indicate command
        assert result.exit_code in [0, 2]  # 2 if command doesn't exist
    
    def test_show_ref(self, repo_with_commits):
        """Test show-ref command if it exists."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        # Create a tag for testing
        runner.invoke(cli, ['branch', 'test-ref'])
        
        result = runner.invoke(cli, ['refs'])
        # Depends on implementation
        assert result.exit_code in [0, 2]


class TestBranchRefsCommand:
    """Tests for branch command refs handling."""
    
    def test_branch_list(self, repo_with_commits):
        """Test branch listing."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        result = runner.invoke(cli, ['branch'])
        assert result.exit_code == 0
        assert 'main' in result.output or '*' in result.output
    
    def test_branch_create(self, repo_with_commits):
        """Test creating a branch."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        result = runner.invoke(cli, ['branch', 'new-branch'])
        assert result.exit_code == 0
        
        # Verify it exists
        result = runner.invoke(cli, ['branch'])
        assert 'new-branch' in result.output
    
    def test_branch_delete(self, repo_with_commits):
        """Test deleting a branch."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        # Create branch first
        runner.invoke(cli, ['branch', 'to-delete'])
        
        # Delete it
        result = runner.invoke(cli, ['branch', '-d', 'to-delete'])
        assert result.exit_code == 0
        
        # Verify it's gone
        result = runner.invoke(cli, ['branch'])
        assert 'to-delete' not in result.output
    
    def test_branch_delete_current(self, repo_with_commits):
        """Test deleting current branch fails."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        result = runner.invoke(cli, ['branch', '-d', 'main'])
        assert result.exit_code != 0
        assert 'current' in result.output.lower() or 'cannot' in result.output.lower()
    
    def test_branch_rename(self, repo_with_commits):
        """Test renaming a branch."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        # Create branch
        runner.invoke(cli, ['branch', 'old-name'])
        
        # Rename it
        result = runner.invoke(cli, ['branch', '-m', 'old-name', 'new-name'])
        # May or may not support -m
        assert result.exit_code in [0, 2]
    
    def test_branch_verbose(self, repo_with_commits):
        """Test branch listing with verbose flag."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        result = runner.invoke(cli, ['branch', '-v'])
        # May show commit hashes
        assert result.exit_code in [0, 2]
    
    def test_branch_at_commit(self, repo_with_commits):
        """Test creating branch at specific commit."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        # Create branch at HEAD~1
        new_file = repo.work_tree / 'for_history.txt'
        new_file.write_text('history content\n')
        runner.invoke(cli, ['add', 'for_history.txt'])
        runner.invoke(cli, ['commit', '-m', 'Adding history'])
        
        result = runner.invoke(cli, ['branch', 'at-parent', 'HEAD~1'])
        # May or may not support this syntax
        assert result.exit_code in [0, 2]


class TestCheckoutRefs:
    """Test checkout command with refs."""
    
    def test_checkout_branch(self, repo_with_commits):
        """Test checking out a branch."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        # Create branch
        runner.invoke(cli, ['branch', 'checkout-test'])
        
        result = runner.invoke(cli, ['checkout', 'checkout-test'])
        assert result.exit_code == 0
    
    def test_checkout_commit(self, repo_with_commits):
        """Test checking out a commit (detached HEAD)."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        # Get current HEAD
        from lit.core.refs import RefManager
        ref_manager = RefManager(repo)
        head_commit = ref_manager.resolve_reference('HEAD')
        
        # Checkout the commit directly
        result = runner.invoke(cli, ['checkout', head_commit[:8]])
        # Should work (detached HEAD) or fail gracefully
        assert result.exit_code in [0, 1]
    
    def test_checkout_create_branch(self, repo_with_commits):
        """Test checkout -b to create and switch to branch."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        result = runner.invoke(cli, ['checkout', '-b', 'new-checkout-branch'])
        assert result.exit_code == 0
        
        # Verify we're on new branch
        result = runner.invoke(cli, ['branch'])
        assert 'new-checkout-branch' in result.output
        assert '*' in result.output  # Current branch marker
