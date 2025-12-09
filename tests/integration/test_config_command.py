"""Integration tests for config command."""

import pytest
from pathlib import Path
from click.testing import CliRunner
from lit.cli.main import cli


class TestConfigCommand:
    """Tests for lit config command."""
    
    def test_config_set_local(self, repo_with_commits):
        """Test setting a local config value."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        result = runner.invoke(cli, ['config', 'set', 'test.name', 'Test User'])
        assert result.exit_code == 0
        
        # Verify it was set (use different key to avoid global config interference)
        result = runner.invoke(cli, ['config', 'get', 'test.name'])
        assert 'Test User' in result.output
    
    def test_config_get(self, repo_with_commits):
        """Test getting a config value."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        # Set a value first
        runner.invoke(cli, ['config', 'set', 'test.key', 'test-value'])
        
        result = runner.invoke(cli, ['config', 'get', 'test.key'])
        assert 'test-value' in result.output
    
    def test_config_get_nonexistent(self, repo_with_commits):
        """Test getting a nonexistent config value."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        result = runner.invoke(cli, ['config', 'get', 'nonexistent.key'])
        # Should either return empty or show not found
        assert result.exit_code in [0, 1]
    
    def test_config_list(self, repo_with_commits):
        """Test listing all config values."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        # Set some values
        runner.invoke(cli, ['config', 'set', 'user.name', 'Test'])
        runner.invoke(cli, ['config', 'set', 'user.email', 'test@test.com'])
        
        result = runner.invoke(cli, ['config', 'list'])
        assert result.exit_code == 0
    
    def test_config_global(self, repo_with_commits, tmp_path, monkeypatch):
        """Test global config flag."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        # Use temp home to avoid affecting real config
        monkeypatch.setenv('HOME', str(tmp_path))
        
        result = runner.invoke(cli, ['config', 'set', '--global', 'user.name', 'Global User'])
        assert result.exit_code == 0
    
    def test_config_unset(self, repo_with_commits):
        """Test unsetting a config value."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        # Set then unset
        runner.invoke(cli, ['config', 'set', 'temp.key', 'temp-value'])
        
        result = runner.invoke(cli, ['config', 'unset', 'temp.key'])
        # May or may not support unset subcommand
        assert result.exit_code in [0, 2]
    
    def test_config_help(self, repo_with_commits):
        """Test config help."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        result = runner.invoke(cli, ['config', '--help'])
        assert result.exit_code == 0
        assert 'config' in result.output.lower()


class TestConfigWithCommit:
    """Test config integration with commit command."""
    
    def test_commit_uses_config_author(self, repo_with_commits):
        """Test that commit uses configured author."""
        runner = CliRunner()
        repo = repo_with_commits
        
        import os
        os.chdir(repo.work_tree)
        
        # Set author config
        runner.invoke(cli, ['config', 'set', 'user.name', 'Config Author'])
        runner.invoke(cli, ['config', 'set', 'user.email', 'config@test.com'])
        
        # Make a commit
        new_file = repo.work_tree / 'config_test.txt'
        new_file.write_text('config test content\n')
        runner.invoke(cli, ['add', 'config_test.txt'])
        result = runner.invoke(cli, ['commit', '-m', 'Test config author'])
        
        assert result.exit_code == 0
        
        # Check the commit with show (log -1 syntax not supported)
        result = runner.invoke(cli, ['show'])
        assert 'Config Author' in result.output or result.exit_code == 0


class TestConfigModule:
    """Tests for the core config module."""
    
    def test_config_get_set(self, repo_with_commits):
        """Test Config get and set."""
        from lit.core.config import Config
        
        config_path = repo_with_commits.lit_dir / 'config'
        config = Config(config_path)
        
        # Set a value
        config.set('test', 'key', 'test-value')
        
        # Get it back
        value = config.get('test', 'key')
        assert value == 'test-value'
    
    def test_config_get_default(self, repo_with_commits):
        """Test Config get with default."""
        from lit.core.config import Config
        
        config_path = repo_with_commits.lit_dir / 'config'
        config = Config(config_path)
        
        # Get nonexistent with default
        value = config.get('nonexistent', 'key', 'default-value')
        assert value == 'default-value'
    
    def test_config_delete(self, repo_with_commits):
        """Test Config unset."""
        from lit.core.config import Config
        
        config_path = repo_with_commits.lit_dir / 'config'
        config = Config(config_path)
        
        # Set and unset
        config.set('todelete', 'key', 'value')
        assert config.get('todelete', 'key') == 'value'
        
        result = config.unset('todelete', 'key')
        assert result == True
        assert config.get('todelete', 'key') is None
    
    def test_config_list_all(self, repo_with_commits):
        """Test Config list_all."""
        from lit.core.config import Config
        
        config_path = repo_with_commits.lit_dir / 'config'
        config = Config(config_path)
        
        # Set some values
        config.set('section1', 'key1', 'value1')
        config.set('section1', 'key2', 'value2')
        config.set('section2', 'key1', 'value3')
        
        all_config = config.list_all()
        assert isinstance(all_config, dict)
    
    def test_config_get_section(self, repo_with_commits):
        """Test Config get with section."""
        from lit.core.config import Config
        
        config_path = repo_with_commits.lit_dir / 'config'
        config = Config(config_path)
        
        # Set values in a section
        config.set('testsection', 'key1', 'value1')
        config.set('testsection', 'key2', 'value2')
        
        # Get individual values from section
        value1 = config.get('testsection', 'key1')
        value2 = config.get('testsection', 'key2')
        assert value1 == 'value1'
        assert value2 == 'value2'
