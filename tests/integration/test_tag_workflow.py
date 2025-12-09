"""Integration tests for tag command workflow."""

import pytest
from pathlib import Path
from click.testing import CliRunner

from lit.cli.main import cli


class TestTagCreate:
    """Tests for creating tags."""
    
    def test_create_tag_on_head(self, tmp_path):
        """Create a tag on HEAD."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file.txt').write_text('content')
            runner.invoke(cli, ['add', 'file.txt'])
            runner.invoke(cli, ['commit', '-m', 'Initial'])
            
            result = runner.invoke(cli, ['tag', 'v1.0'])
            assert result.exit_code == 0
            assert "Created tag 'v1.0'" in result.output
    
    def test_create_tag_on_specific_commit(self, tmp_path):
        """Create a tag on a specific commit."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file.txt').write_text('first')
            runner.invoke(cli, ['add', 'file.txt'])
            runner.invoke(cli, ['commit', '-m', 'First'])
            
            Path('file.txt').write_text('second')
            runner.invoke(cli, ['add', 'file.txt'])
            runner.invoke(cli, ['commit', '-m', 'Second'])
            
            result = runner.invoke(cli, ['tag', 'v0.1', 'HEAD~1'])
            assert result.exit_code == 0
            assert "Created tag 'v0.1'" in result.output
    
    def test_tag_already_exists(self, tmp_path):
        """Creating duplicate tag should fail."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file.txt').write_text('content')
            runner.invoke(cli, ['add', 'file.txt'])
            runner.invoke(cli, ['commit', '-m', 'Initial'])
            
            runner.invoke(cli, ['tag', 'v1.0'])
            result = runner.invoke(cli, ['tag', 'v1.0'])
            assert result.exit_code != 0
            assert "already exists" in result.output
    
    def test_tag_force_replace(self, tmp_path):
        """Force replacing an existing tag."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file.txt').write_text('first')
            runner.invoke(cli, ['add', 'file.txt'])
            runner.invoke(cli, ['commit', '-m', 'First'])
            
            runner.invoke(cli, ['tag', 'v1.0'])
            
            Path('file.txt').write_text('second')
            runner.invoke(cli, ['add', 'file.txt'])
            runner.invoke(cli, ['commit', '-m', 'Second'])
            
            result = runner.invoke(cli, ['tag', '-f', 'v1.0'])
            assert result.exit_code == 0
            assert "Created tag 'v1.0'" in result.output


class TestTagList:
    """Tests for listing tags."""
    
    def test_list_tags_empty(self, tmp_path):
        """List tags when none exist."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file.txt').write_text('content')
            runner.invoke(cli, ['add', 'file.txt'])
            runner.invoke(cli, ['commit', '-m', 'Initial'])
            
            result = runner.invoke(cli, ['tag'])
            assert result.exit_code == 0
            assert "No tags found" in result.output
    
    def test_list_tags(self, tmp_path):
        """List existing tags."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file.txt').write_text('content')
            runner.invoke(cli, ['add', 'file.txt'])
            runner.invoke(cli, ['commit', '-m', 'Initial'])
            
            runner.invoke(cli, ['tag', 'v1.0'])
            runner.invoke(cli, ['tag', 'v2.0'])
            
            result = runner.invoke(cli, ['tag', '-l'])
            assert result.exit_code == 0
            assert 'v1.0' in result.output
            assert 'v2.0' in result.output
    
    def test_list_tags_shows_commit_info(self, tmp_path):
        """Tag list should show commit info."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file.txt').write_text('content')
            runner.invoke(cli, ['add', 'file.txt'])
            runner.invoke(cli, ['commit', '-m', 'Initial commit'])
            
            runner.invoke(cli, ['tag', 'v1.0'])
            
            result = runner.invoke(cli, ['tag'])
            assert result.exit_code == 0
            assert 'v1.0' in result.output
            assert 'Initial commit' in result.output


class TestTagDelete:
    """Tests for deleting tags."""
    
    def test_delete_tag(self, tmp_path):
        """Delete an existing tag."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file.txt').write_text('content')
            runner.invoke(cli, ['add', 'file.txt'])
            runner.invoke(cli, ['commit', '-m', 'Initial'])
            
            runner.invoke(cli, ['tag', 'v1.0'])
            result = runner.invoke(cli, ['tag', '-d', 'v1.0'])
            assert result.exit_code == 0
            assert "Deleted tag 'v1.0'" in result.output
            
            # Verify it's gone
            list_result = runner.invoke(cli, ['tag'])
            assert 'v1.0' not in list_result.output
    
    def test_delete_nonexistent_tag(self, tmp_path):
        """Delete non-existent tag should fail."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file.txt').write_text('content')
            runner.invoke(cli, ['add', 'file.txt'])
            runner.invoke(cli, ['commit', '-m', 'Initial'])
            
            result = runner.invoke(cli, ['tag', '-d', 'nonexistent'])
            assert result.exit_code != 0
            assert "not found" in result.output


class TestTagValidation:
    """Tests for tag name validation."""
    
    def test_invalid_tag_name_with_space(self, tmp_path):
        """Tag name with space should fail."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file.txt').write_text('content')
            runner.invoke(cli, ['add', 'file.txt'])
            runner.invoke(cli, ['commit', '-m', 'Initial'])
            
            result = runner.invoke(cli, ['tag', 'v 1.0'])
            assert result.exit_code != 0
            assert "Invalid tag name" in result.output
    
    def test_tag_no_commits(self, tmp_path):
        """Creating tag with no commits should fail."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            
            result = runner.invoke(cli, ['tag', 'v1.0'])
            assert result.exit_code != 0
            assert "No commits" in result.output


class TestTagHelp:
    """Tests for tag help."""
    
    def test_tag_help(self):
        """Tag --help should show usage."""
        runner = CliRunner()
        result = runner.invoke(cli, ['tag', '--help'])
        assert result.exit_code == 0
        assert '--annotate' in result.output
        assert '--delete' in result.output
        assert '--force' in result.output
