"""Tests for checkout command with remote tracking branches."""

import pytest
from pathlib import Path
from click.testing import CliRunner

from lit.cli.commands.checkout import (
    checkout_cmd, 
    find_remote_tracking_branch, 
    create_tracking_branch,
    branch_exists
)
from lit.core.repository import Repository
from lit.core.objects import Commit, Tree, Blob


class TestRemoteTrackingBranches:
    """Tests for checking out remote-tracking branches."""
    
    def test_find_remote_tracking_branch_exists(self, tmp_path):
        """Test finding a remote-tracking branch that exists."""
        repo = Repository(str(tmp_path))
        repo.init()
        
        # Create remote-tracking ref
        remote_ref_dir = repo.lit_dir / 'refs' / 'remotes' / 'origin'
        remote_ref_dir.mkdir(parents=True)
        (remote_ref_dir / 'feature').write_text('abc123\n')
        
        result = find_remote_tracking_branch(repo, 'feature')
        
        assert result is not None
        remote_name, ref_path, commit_hash = result
        assert remote_name == 'origin'
        assert ref_path == 'refs/remotes/origin/feature'
        assert commit_hash == 'abc123'
    
    def test_find_remote_tracking_branch_not_exists(self, tmp_path):
        """Test finding a remote-tracking branch that doesn't exist."""
        repo = Repository(str(tmp_path))
        repo.init()
        
        result = find_remote_tracking_branch(repo, 'nonexistent')
        
        assert result is None
    
    def test_find_remote_tracking_branch_no_remotes_dir(self, tmp_path):
        """Test finding remote-tracking branch when remotes dir doesn't exist."""
        repo = Repository(str(tmp_path))
        repo.init()
        
        # Ensure remotes dir doesn't exist
        remotes_dir = repo.lit_dir / 'refs' / 'remotes'
        if remotes_dir.exists():
            import shutil
            shutil.rmtree(remotes_dir)
        
        result = find_remote_tracking_branch(repo, 'feature')
        
        assert result is None
    
    def test_create_tracking_branch(self, tmp_path):
        """Test creating a tracking branch."""
        repo = Repository(str(tmp_path))
        repo.init()
        
        commit_hash = 'abc123def456'
        create_tracking_branch(repo, 'feature', 'origin', commit_hash)
        
        branch_file = repo.lit_dir / 'refs' / 'heads' / 'feature'
        assert branch_file.exists()
        assert branch_file.read_text().strip() == commit_hash


class TestCheckoutAutoTracking:
    """Tests for auto-tracking behavior when checking out remote branches."""
    
    @pytest.fixture
    def repo_with_remote_branch(self, tmp_path):
        """Create a repo with a remote-tracking branch."""
        repo = Repository(str(tmp_path))
        repo.init()
        
        # Create initial commit on main
        blob = Blob(b'content')
        blob_hash = repo.write_object(blob)
        
        tree = Tree()
        tree.add_entry('100644', 'blob', blob_hash, 'file.txt')
        tree_hash = repo.write_object(tree)
        
        commit = Commit.create(
            tree_hash=tree_hash,
            parent_hashes=[],
            author='Test <test@test.com>',
            committer='Test <test@test.com>',
            message='Initial commit'
        )
        commit_hash = repo.write_object(commit)
        
        # Set up main branch
        (repo.lit_dir / 'refs' / 'heads' / 'main').write_text(commit_hash + '\n')
        repo.head_file.write_text('ref: refs/heads/main\n')
        
        # Create remote-tracking branch
        remote_ref_dir = repo.lit_dir / 'refs' / 'remotes' / 'origin'
        remote_ref_dir.mkdir(parents=True)
        (remote_ref_dir / 'feature').write_text(commit_hash + '\n')
        
        # Write file to working tree
        (tmp_path / 'file.txt').write_text('content')
        
        return repo, commit_hash
    
    def test_checkout_creates_tracking_branch(self, repo_with_remote_branch, tmp_path, monkeypatch):
        """Test that checking out a name matching a remote branch creates a tracking branch."""
        repo, commit_hash = repo_with_remote_branch
        monkeypatch.chdir(tmp_path)
        
        # Verify feature branch doesn't exist locally
        assert not branch_exists(repo, 'feature')
        
        runner = CliRunner()
        result = runner.invoke(checkout_cmd, ['feature'])
        
        # Should succeed and create tracking branch
        assert result.exit_code == 0
        assert "tracking" in result.output.lower()
        
        # Local branch should now exist
        assert branch_exists(repo, 'feature')
        
        # HEAD should point to the new branch
        head_content = repo.head_file.read_text().strip()
        assert head_content == 'ref: refs/heads/feature'


class TestCheckoutDetachFlag:
    """Tests for --detach flag behavior."""
    
    @pytest.fixture
    def repo_with_branch(self, tmp_path):
        """Create a repo with a branch."""
        repo = Repository(str(tmp_path))
        repo.init()
        
        blob = Blob(b'content')
        blob_hash = repo.write_object(blob)
        
        tree = Tree()
        tree.add_entry('100644', 'blob', blob_hash, 'file.txt')
        tree_hash = repo.write_object(tree)
        
        commit = Commit.create(
            tree_hash=tree_hash,
            parent_hashes=[],
            author='Test <test@test.com>',
            committer='Test <test@test.com>',
            message='Initial commit'
        )
        commit_hash = repo.write_object(commit)
        
        (repo.lit_dir / 'refs' / 'heads' / 'main').write_text(commit_hash + '\n')
        repo.head_file.write_text('ref: refs/heads/main\n')
        
        (tmp_path / 'file.txt').write_text('content')
        
        return repo, commit_hash
    
    def test_checkout_detach_on_branch(self, repo_with_branch, tmp_path, monkeypatch):
        """Test --detach flag creates detached HEAD at branch."""
        repo, commit_hash = repo_with_branch
        monkeypatch.chdir(tmp_path)
        
        runner = CliRunner()
        result = runner.invoke(checkout_cmd, ['--detach', 'main'])
        
        assert result.exit_code == 0
        assert "detached HEAD" in result.output
        
        head_content = repo.head_file.read_text().strip()
        assert head_content == commit_hash
