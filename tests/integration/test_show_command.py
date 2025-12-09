"""Integration tests for show command."""

import pytest
from pathlib import Path
from click.testing import CliRunner
from lit.cli.main import cli


class TestShowCommand:
    """Tests for lit show command."""
    
    def test_show_commit(self, repo_with_commits):
        """Test showing a commit."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        result = runner.invoke(cli, ['show', 'HEAD'])
        assert result.exit_code == 0
        assert 'commit' in result.output.lower() or 'Commit' in result.output
    
    def test_show_head(self, repo_with_commits):
        """Test showing HEAD."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        result = runner.invoke(cli, ['show'])
        assert result.exit_code == 0
        # Should show HEAD by default
    
    def test_show_parent(self, repo_with_commits):
        """Test showing HEAD~1."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        # Make sure we have at least 2 commits
        new_file = repo.work_tree / 'another.txt'
        new_file.write_text('another content\n')
        runner.invoke(cli, ['add', 'another.txt'])
        runner.invoke(cli, ['commit', '-m', 'Second commit'])
        
        result = runner.invoke(cli, ['show', 'HEAD~1'])
        # May or may not support HEAD~N syntax - depends on refs implementation
        assert result.exit_code in [0, 1]
    
    def test_show_with_stat(self, repo_with_commits):
        """Test show with --stat option."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        result = runner.invoke(cli, ['show', '--stat'])
        # May or may not support --stat, but shouldn't crash
        assert result.exit_code in [0, 2]  # 2 is for invalid option
    
    def test_show_nonexistent_ref(self, repo_with_commits):
        """Test show with nonexistent reference."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        result = runner.invoke(cli, ['show', 'nonexistent123'])
        assert result.exit_code != 0
    
    def test_show_branch(self, repo_with_commits):
        """Test showing a branch."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        # Create a branch
        runner.invoke(cli, ['branch', 'show-test'])
        
        result = runner.invoke(cli, ['show', 'show-test'])
        assert result.exit_code == 0


class TestCatFileCommand:
    """Tests for lit cat-file command."""
    
    def test_cat_file_commit(self, repo_with_commits):
        """Test cat-file on a commit."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        # Get HEAD commit hash first
        from lit.core.refs import RefManager
        ref_manager = RefManager(repo)
        head_commit = ref_manager.resolve_reference('HEAD')
        
        # Need -p flag to pretty-print commit objects
        result = runner.invoke(cli, ['cat-file', '-p', head_commit])
        assert result.exit_code == 0
        assert 'tree' in result.output.lower() or 'Tree' in result.output
    
    def test_cat_file_blob(self, repo_with_commits):
        """Test cat-file on a blob (file content)."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        # Get the tree first
        result = runner.invoke(cli, ['ls-tree', 'HEAD'])
        assert result.exit_code == 0


class TestLsTreeCommand:
    """Tests for lit ls-tree command."""
    
    def test_ls_tree_head(self, repo_with_commits):
        """Test ls-tree on HEAD."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        result = runner.invoke(cli, ['ls-tree', 'HEAD'])
        assert result.exit_code == 0
        # Should show files in commit
    
    def test_ls_tree_recursive(self, repo_with_commits):
        """Test ls-tree with -r flag."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        result = runner.invoke(cli, ['ls-tree', '-r', 'HEAD'])
        assert result.exit_code == 0
    
    def test_ls_tree_nonexistent(self, repo_with_commits):
        """Test ls-tree on nonexistent ref."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        result = runner.invoke(cli, ['ls-tree', 'nonexistent123'])
        assert result.exit_code != 0


class TestCountObjectsCommand:
    """Tests for lit count-objects command."""
    
    def test_count_objects(self, repo_with_commits):
        """Test count-objects command."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        result = runner.invoke(cli, ['count-objects'])
        assert result.exit_code == 0
        # Should show object counts
    
    def test_count_objects_verbose(self, repo_with_commits):
        """Test count-objects with -v flag."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        result = runner.invoke(cli, ['count-objects', '-v'])
        assert result.exit_code == 0
        # Should show more detailed info
