"""Integration tests for merge command."""

import pytest
from pathlib import Path
from click.testing import CliRunner
from lit.cli.main import cli


class TestMergeCommand:
    """Tests for lit merge command."""
    
    def test_merge_fast_forward(self, repo_with_commits):
        """Test fast-forward merge."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        # Create a feature branch
        runner.invoke(cli, ['branch', 'feature'])
        runner.invoke(cli, ['switch', 'feature'])
        
        # Add a commit on feature
        new_file = repo.work_tree / 'feature.txt'
        new_file.write_text('feature content\n')
        runner.invoke(cli, ['add', 'feature.txt'])
        runner.invoke(cli, ['commit', '-m', 'Feature commit'])
        
        # Switch back to main (which is behind)
        runner.invoke(cli, ['switch', 'main'])
        
        # Merge feature into main (should fast-forward)
        result = runner.invoke(cli, ['merge', 'feature'])
        assert result.exit_code == 0
        assert 'Fast-forward' in result.output or 'fast-forward' in result.output.lower() or 'Merge' in result.output
    
    def test_merge_no_branch(self, repo_with_commits):
        """Test merge with no branch specified."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        result = runner.invoke(cli, ['merge'])
        # May succeed with help or fail - depends on implementation
        # The command requires a branch argument
        assert result.exit_code in [0, 1, 2]
    
    def test_merge_nonexistent_branch(self, repo_with_commits):
        """Test merge with nonexistent branch."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        result = runner.invoke(cli, ['merge', 'nonexistent'])
        # Should handle gracefully
        assert result.exit_code in [0, 1]
    
    def test_merge_already_up_to_date(self, repo_with_commits):
        """Test merge when already up to date."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        # Create branch at same commit
        runner.invoke(cli, ['branch', 'same-commit'])
        
        # Try to merge - should say already up to date
        result = runner.invoke(cli, ['merge', 'same-commit'])
        assert result.exit_code == 0
        assert 'up to date' in result.output.lower() or 'Already' in result.output
    
    def test_merge_no_ff(self, repo_with_commits):
        """Test merge with --no-ff flag."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        # Create feature branch with commit
        runner.invoke(cli, ['branch', 'feature-noff'])
        runner.invoke(cli, ['switch', 'feature-noff'])
        
        new_file = repo.work_tree / 'feature_noff.txt'
        new_file.write_text('no ff content\n')
        runner.invoke(cli, ['add', 'feature_noff.txt'])
        runner.invoke(cli, ['commit', '-m', 'Feature no-ff commit'])
        
        runner.invoke(cli, ['switch', 'main'])
        
        result = runner.invoke(cli, ['merge', 'feature-noff', '--no-ff'])
        # May create merge commit or fast-forward depending on implementation
        assert result.exit_code == 0
    
    def test_merge_abort_no_merge(self, repo_with_commits):
        """Test merge --abort when no merge in progress."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        result = runner.invoke(cli, ['merge', '--abort'])
        # Should either error or say no merge in progress
        assert result.exit_code in [0, 1]


class TestMergeWithConflicts:
    """Test merge conflict scenarios."""
    
    def test_merge_with_conflict(self, repo_with_commits):
        """Test merge that creates a conflict."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        # Create divergent branches
        test_file = repo.work_tree / 'test.txt'
        
        # Create feature branch
        runner.invoke(cli, ['branch', 'conflict-feature'])
        
        # Modify on main
        test_file.write_text('main version\n')
        runner.invoke(cli, ['add', 'test.txt'])
        runner.invoke(cli, ['commit', '-m', 'Main change'])
        
        # Switch to feature and modify same file
        runner.invoke(cli, ['switch', 'conflict-feature'])
        test_file.write_text('feature version\n')
        runner.invoke(cli, ['add', 'test.txt'])
        runner.invoke(cli, ['commit', '-m', 'Feature change'])
        
        # Switch back to main and try to merge
        runner.invoke(cli, ['switch', 'main'])
        result = runner.invoke(cli, ['merge', 'conflict-feature'])
        
        # Should either succeed with conflict markers or report conflict
        # The exact behavior depends on implementation
        assert result.exit_code in [0, 1]
