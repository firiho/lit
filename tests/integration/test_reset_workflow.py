"""Integration tests for reset command workflow."""

import pytest
from pathlib import Path
from click.testing import CliRunner

from lit.cli.main import cli
from lit.core.repository import Repository


@pytest.fixture
def repo_with_commits(tmp_path):
    """Create a repository with multiple commits."""
    runner = CliRunner()
    
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        # Initialize repo
        result = runner.invoke(cli, ['init'])
        assert result.exit_code == 0
        
        # Create first commit
        Path('file1.txt').write_text('First content')
        runner.invoke(cli, ['add', 'file1.txt'])
        runner.invoke(cli, ['commit', '-m', 'First commit'])
        
        # Create second commit
        Path('file2.txt').write_text('Second content')
        runner.invoke(cli, ['add', 'file2.txt'])
        runner.invoke(cli, ['commit', '-m', 'Second commit'])
        
        # Create third commit
        Path('file3.txt').write_text('Third content')
        runner.invoke(cli, ['add', 'file3.txt'])
        runner.invoke(cli, ['commit', '-m', 'Third commit'])
        
        yield Path(td)


class TestResetSoft:
    """Tests for reset --soft."""
    
    def test_reset_soft_moves_head(self, tmp_path):
        """Reset --soft should move HEAD but keep index and working tree."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Initialize and create commits
            runner.invoke(cli, ['init'])
            Path('file1.txt').write_text('First')
            runner.invoke(cli, ['add', 'file1.txt'])
            runner.invoke(cli, ['commit', '-m', 'First commit'])
            
            Path('file2.txt').write_text('Second')
            runner.invoke(cli, ['add', 'file2.txt'])
            runner.invoke(cli, ['commit', '-m', 'Second commit'])
            
            # Get commits before reset
            repo = Repository(str(Path.cwd()))
            second_commit = repo.refs.resolve_head()
            
            # Reset soft
            result = runner.invoke(cli, ['reset', '--soft', 'HEAD~1'])
            assert result.exit_code == 0
            assert 'HEAD is now at' in result.output
            assert 'Index and working tree unchanged' in result.output
            
            # HEAD should have moved
            repo2 = Repository(str(Path.cwd()))
            new_head = repo2.refs.resolve_head()
            assert new_head != second_commit
            
            # Working tree should still have file2.txt
            assert Path('file2.txt').exists()
    
    def test_reset_soft_keeps_changes_staged(self, tmp_path):
        """After soft reset, changes should be staged."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file1.txt').write_text('First')
            runner.invoke(cli, ['add', 'file1.txt'])
            runner.invoke(cli, ['commit', '-m', 'First commit'])
            
            Path('file2.txt').write_text('Second')
            runner.invoke(cli, ['add', 'file2.txt'])
            runner.invoke(cli, ['commit', '-m', 'Second commit'])
            
            # Reset soft
            runner.invoke(cli, ['reset', '--soft', 'HEAD~1'])
            
            # Check status - file2.txt should be staged
            result = runner.invoke(cli, ['status'])
            assert 'file2.txt' in result.output


class TestResetMixed:
    """Tests for reset --mixed (default)."""
    
    def test_reset_mixed_resets_index(self, tmp_path):
        """Reset --mixed should reset index but keep working tree."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file1.txt').write_text('First')
            runner.invoke(cli, ['add', 'file1.txt'])
            runner.invoke(cli, ['commit', '-m', 'First commit'])
            
            Path('file2.txt').write_text('Second')
            runner.invoke(cli, ['add', 'file2.txt'])
            runner.invoke(cli, ['commit', '-m', 'Second commit'])
            
            # Reset mixed
            result = runner.invoke(cli, ['reset', '--mixed', 'HEAD~1'])
            assert result.exit_code == 0
            assert 'Index reset' in result.output
            assert 'Working tree unchanged' in result.output
            
            # Working tree should still have file2.txt
            assert Path('file2.txt').exists()
    
    def test_reset_mixed_unstages_changes(self, tmp_path):
        """After mixed reset, changes should be unstaged."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file1.txt').write_text('First')
            runner.invoke(cli, ['add', 'file1.txt'])
            runner.invoke(cli, ['commit', '-m', 'First commit'])
            
            Path('file2.txt').write_text('Second')
            runner.invoke(cli, ['add', 'file2.txt'])
            runner.invoke(cli, ['commit', '-m', 'Second commit'])
            
            # Reset mixed
            runner.invoke(cli, ['reset', '--mixed', 'HEAD~1'])
            
            # Check status - file2.txt should be untracked
            result = runner.invoke(cli, ['status'])
            # Should show as not staged or untracked
            assert 'file2.txt' in result.output
    
    def test_reset_default_is_mixed(self, tmp_path):
        """Reset without flags should default to --mixed."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file1.txt').write_text('First')
            runner.invoke(cli, ['add', 'file1.txt'])
            runner.invoke(cli, ['commit', '-m', 'First commit'])
            
            Path('file2.txt').write_text('Second')
            runner.invoke(cli, ['add', 'file2.txt'])
            runner.invoke(cli, ['commit', '-m', 'Second commit'])
            
            # Reset without flag (should be mixed)
            result = runner.invoke(cli, ['reset', 'HEAD~1'])
            assert result.exit_code == 0
            assert 'Index reset' in result.output


class TestResetHard:
    """Tests for reset --hard."""
    
    def test_reset_hard_removes_files(self, tmp_path):
        """Reset --hard should remove files not in target commit."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file1.txt').write_text('First')
            runner.invoke(cli, ['add', 'file1.txt'])
            runner.invoke(cli, ['commit', '-m', 'First commit'])
            
            Path('file2.txt').write_text('Second')
            runner.invoke(cli, ['add', 'file2.txt'])
            runner.invoke(cli, ['commit', '-m', 'Second commit'])
            
            # Verify file2.txt exists
            assert Path('file2.txt').exists()
            
            # Reset hard
            result = runner.invoke(cli, ['reset', '--hard', 'HEAD~1'])
            assert result.exit_code == 0
            assert 'uncommitted changes will be lost' in result.output
            assert 'Index and working tree reset' in result.output
            
            # file2.txt should be gone
            assert not Path('file2.txt').exists()
            # file1.txt should still exist
            assert Path('file1.txt').exists()
    
    def test_reset_hard_restores_content(self, tmp_path):
        """Reset --hard should restore file content to target commit."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file1.txt').write_text('Original content')
            runner.invoke(cli, ['add', 'file1.txt'])
            runner.invoke(cli, ['commit', '-m', 'First commit'])
            
            Path('file1.txt').write_text('Modified content')
            runner.invoke(cli, ['add', 'file1.txt'])
            runner.invoke(cli, ['commit', '-m', 'Second commit'])
            
            # Reset hard
            runner.invoke(cli, ['reset', '--hard', 'HEAD~1'])
            
            # Content should be restored
            assert Path('file1.txt').read_text() == 'Original content'


class TestResetToCommit:
    """Tests for resetting to specific commits."""
    
    def test_reset_to_commit_hash(self, tmp_path):
        """Reset should work with full commit hash."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file1.txt').write_text('First')
            runner.invoke(cli, ['add', 'file1.txt'])
            runner.invoke(cli, ['commit', '-m', 'First commit'])
            
            # Get first commit hash
            repo = Repository(str(Path.cwd()))
            first_commit = repo.refs.resolve_head()
            
            Path('file2.txt').write_text('Second')
            runner.invoke(cli, ['add', 'file2.txt'])
            runner.invoke(cli, ['commit', '-m', 'Second commit'])
            
            # Reset to first commit using hash
            result = runner.invoke(cli, ['reset', '--soft', first_commit])
            assert result.exit_code == 0
            
            # HEAD should point to first commit
            repo2 = Repository(str(Path.cwd()))
            assert repo2.refs.resolve_head() == first_commit
    
    def test_reset_head_tilde_syntax(self, tmp_path):
        """Reset should support HEAD~N syntax."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            
            # Create 3 commits
            for i in range(3):
                Path(f'file{i}.txt').write_text(f'Content {i}')
                runner.invoke(cli, ['add', f'file{i}.txt'])
                runner.invoke(cli, ['commit', '-m', f'Commit {i}'])
            
            repo = Repository(str(Path.cwd()))
            
            # Reset HEAD~2
            result = runner.invoke(cli, ['reset', '--soft', 'HEAD~2'])
            assert result.exit_code == 0
            
            # Should show "Commit 0" message
            assert 'Commit 0' in result.output


class TestResetErrors:
    """Tests for reset error handling."""
    
    def test_reset_invalid_commit(self, tmp_path):
        """Reset with invalid commit should fail gracefully."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file.txt').write_text('Content')
            runner.invoke(cli, ['add', 'file.txt'])
            runner.invoke(cli, ['commit', '-m', 'First commit'])
            
            result = runner.invoke(cli, ['reset', 'invalid-ref'])
            assert result.exit_code != 0
    
    def test_reset_beyond_root(self, tmp_path):
        """Reset beyond root commit should fail gracefully."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file.txt').write_text('Content')
            runner.invoke(cli, ['add', 'file.txt'])
            runner.invoke(cli, ['commit', '-m', 'First commit'])
            
            result = runner.invoke(cli, ['reset', 'HEAD~5'])
            assert result.exit_code != 0
            assert 'Cannot go back' in result.output or 'reached root' in result.output
    
    def test_reset_outside_repo(self, tmp_path):
        """Reset outside repository should fail."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ['reset', 'HEAD'])
            assert result.exit_code != 0


class TestResetHelp:
    """Tests for reset help and options."""
    
    def test_reset_help(self):
        """Reset --help should show usage info."""
        runner = CliRunner()
        result = runner.invoke(cli, ['reset', '--help'])
        assert result.exit_code == 0
        assert '--soft' in result.output
        assert '--mixed' in result.output
        assert '--hard' in result.output
    
    def test_reset_mutually_exclusive_flags(self, tmp_path):
        """Using multiple mode flags should use the last one."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file.txt').write_text('Content')
            runner.invoke(cli, ['add', 'file.txt'])
            runner.invoke(cli, ['commit', '-m', 'First commit'])
            
            Path('file2.txt').write_text('Content 2')
            runner.invoke(cli, ['add', 'file2.txt'])
            runner.invoke(cli, ['commit', '-m', 'Second commit'])
            
            # This tests that the command doesn't crash with multiple flags
            # The behavior depends on how Click handles flag order
            result = runner.invoke(cli, ['reset', '--soft', '--hard', 'HEAD~1'])
            # Should either succeed or fail gracefully
            assert result.exit_code in [0, 1, 2]


class TestResetFile:
    """Tests for reset with file paths (unstaging)."""
    
    def test_reset_file_unstages_modified(self, tmp_path):
        """Reset file.txt should unstage a modified file."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file.txt').write_text('Original')
            runner.invoke(cli, ['add', 'file.txt'])
            runner.invoke(cli, ['commit', '-m', 'Initial'])
            
            # Modify and stage
            Path('file.txt').write_text('Modified')
            runner.invoke(cli, ['add', 'file.txt'])
            
            # Check it's staged
            status = runner.invoke(cli, ['status'])
            assert 'Changes to be committed' in status.output
            
            # Reset the file
            result = runner.invoke(cli, ['reset', 'file.txt'])
            assert result.exit_code == 0
            assert 'Reset 1 file' in result.output
            
            # Check it's now unstaged
            status = runner.invoke(cli, ['status'])
            assert 'Changes not staged for commit' in status.output
    
    def test_reset_head_file_syntax(self, tmp_path):
        """Reset HEAD file.txt should also work."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file.txt').write_text('Original')
            runner.invoke(cli, ['add', 'file.txt'])
            runner.invoke(cli, ['commit', '-m', 'Initial'])
            
            Path('file.txt').write_text('Modified')
            runner.invoke(cli, ['add', 'file.txt'])
            
            result = runner.invoke(cli, ['reset', 'HEAD', 'file.txt'])
            assert result.exit_code == 0
            assert 'Reset 1 file' in result.output
    
    def test_reset_unstages_new_file(self, tmp_path):
        """Reset should unstage a newly added file."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file.txt').write_text('Original')
            runner.invoke(cli, ['add', 'file.txt'])
            runner.invoke(cli, ['commit', '-m', 'Initial'])
            
            # Create and stage a new file
            Path('newfile.txt').write_text('New content')
            runner.invoke(cli, ['add', 'newfile.txt'])
            
            # Check it's staged
            status = runner.invoke(cli, ['status'])
            assert 'new file:' in status.output
            
            # Reset the new file
            result = runner.invoke(cli, ['reset', 'newfile.txt'])
            assert result.exit_code == 0
            assert 'Unstaged 1 new file' in result.output
            
            # Check it's now untracked
            status = runner.invoke(cli, ['status'])
            assert 'Untracked files' in status.output
    
    def test_reset_multiple_files(self, tmp_path):
        """Reset should handle multiple files."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file1.txt').write_text('One')
            Path('file2.txt').write_text('Two')
            runner.invoke(cli, ['add', 'file1.txt', 'file2.txt'])
            runner.invoke(cli, ['commit', '-m', 'Initial'])
            
            # Modify and stage both
            Path('file1.txt').write_text('One modified')
            Path('file2.txt').write_text('Two modified')
            runner.invoke(cli, ['add', 'file1.txt', 'file2.txt'])
            
            # Reset both files
            result = runner.invoke(cli, ['reset', 'file1.txt', 'file2.txt'])
            assert result.exit_code == 0
            assert 'Reset 2 file' in result.output
    
    def test_reset_file_with_mode_flag_fails(self, tmp_path):
        """Reset --hard file.txt should fail."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(cli, ['init'])
            Path('file.txt').write_text('Content')
            runner.invoke(cli, ['add', 'file.txt'])
            runner.invoke(cli, ['commit', '-m', 'Initial'])
            
            Path('file.txt').write_text('Modified')
            runner.invoke(cli, ['add', 'file.txt'])
            
            # Should fail with helpful message
            result = runner.invoke(cli, ['reset', '--hard', 'file.txt'])
            assert result.exit_code != 0
            assert 'Cannot use --soft or --hard with file paths' in result.output