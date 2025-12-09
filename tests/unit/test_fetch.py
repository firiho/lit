"""Tests for fetch command functionality."""

import pytest
from pathlib import Path
from click.testing import CliRunner

from lit.cli.commands.fetch import fetch_cmd
from lit.core.repository import Repository


class TestFetchCommand:
    """Tests for the fetch CLI command."""
    
    def test_fetch_no_repository(self, tmp_path, monkeypatch):
        """Test fetch fails outside a repository."""
        monkeypatch.chdir(tmp_path)
        
        runner = CliRunner()
        result = runner.invoke(fetch_cmd, [])
        
        assert result.exit_code == 0  # Command handles error gracefully
        assert "Not a lit repository" in result.output
    
    def test_fetch_no_remotes(self, tmp_path, monkeypatch):
        """Test fetch fails when no remotes are configured."""
        monkeypatch.chdir(tmp_path)
        
        # Create a repository without remotes
        repo = Repository(str(tmp_path))
        repo.init()
        
        runner = CliRunner()
        result = runner.invoke(fetch_cmd, ['origin'])
        
        assert "Remote 'origin' not found" in result.output
    
    def test_fetch_all_no_remotes(self, tmp_path, monkeypatch):
        """Test fetch --all fails when no remotes configured."""
        monkeypatch.chdir(tmp_path)
        
        repo = Repository(str(tmp_path))
        repo.init()
        
        runner = CliRunner()
        result = runner.invoke(fetch_cmd, ['--all'])
        
        assert "No remotes configured" in result.output


class TestFetchIntegration:
    """Integration tests for fetch with actual remote repositories."""
    
    def test_fetch_from_local_remote(self, tmp_path):
        """Test fetching from a local file:// remote."""
        # Create remote repository
        remote_path = tmp_path / 'remote-repo'
        remote_path.mkdir()
        remote_repo = Repository(str(remote_path))
        remote_repo.init()
        
        # Create a commit in remote
        (remote_path / 'file.txt').write_text('content')
        from lit.core.index import Index
        index = Index()
        index.add_file(remote_repo, str(remote_path / 'file.txt'))
        index.write(str(remote_repo.index_file))
        
        from lit.core.objects import Commit, Tree, Blob
        
        blob = Blob(b'content')
        blob_hash = remote_repo.write_object(blob)
        tree = Tree()
        tree.add_entry('100644', 'blob', blob_hash, 'file.txt')
        tree_hash = remote_repo.write_object(tree)
        
        commit = Commit.create(
            tree_hash=tree_hash,
            parent_hashes=[],
            author='Test <test@test.com>',
            committer='Test <test@test.com>',
            message='Initial commit'
        )
        commit_hash = remote_repo.write_object(commit)
        
        # Create branch
        (remote_repo.lit_dir / 'refs' / 'heads' / 'main').write_text(commit_hash + '\n')
        remote_repo.head_file.write_text('ref: refs/heads/main\n')
        
        # Create local repository (clone-like setup)
        local_path = tmp_path / 'local-repo'
        local_path.mkdir()
        local_repo = Repository(str(local_path))
        local_repo.init()
        
        # Add remote
        local_repo.remote.add_remote('origin', str(remote_path))
        
        # Perform fetch directly (not via CLI to avoid path issues)
        local_repo.remote.fetch('origin')
        
        # Check remote-tracking refs were created
        remote_refs_dir = local_repo.remotes_dir / 'origin'
        assert remote_refs_dir.exists()
        assert (remote_refs_dir / 'main').exists()
        
        # Check objects were fetched
        assert local_repo.object_exists(commit_hash)
    
    def test_fetch_updates_existing_remote_ref(self, tmp_path):
        """Test that fetch updates remote-tracking refs when remote has new commits."""
        # Create remote repository
        remote_path = tmp_path / 'remote-repo'
        remote_path.mkdir()
        remote_repo = Repository(str(remote_path))
        remote_repo.init()
        
        # Create initial commit in remote
        from lit.core.objects import Commit, Tree, Blob
        
        blob = Blob(b'initial')
        blob_hash = remote_repo.write_object(blob)
        
        tree = Tree()
        tree.add_entry('100644', 'blob', blob_hash, 'file.txt')
        tree_hash = remote_repo.write_object(tree)
        
        commit1 = Commit.create(
            tree_hash=tree_hash,
            parent_hashes=[],
            author='Test <test@test.com>',
            committer='Test <test@test.com>',
            message='Initial commit'
        )
        commit1_hash = remote_repo.write_object(commit1)
        
        (remote_repo.lit_dir / 'refs' / 'heads' / 'main').write_text(commit1_hash + '\n')
        remote_repo.head_file.write_text('ref: refs/heads/main\n')
        
        # Create local repository with remote
        local_path = tmp_path / 'local-repo'
        local_path.mkdir()
        local_repo = Repository(str(local_path))
        local_repo.init()
        local_repo.remote.add_remote('origin', str(remote_path))
        
        # First fetch
        local_repo.remote.fetch('origin')
        
        # Create second commit in remote
        blob2 = Blob(b'updated')
        blob2_hash = remote_repo.write_object(blob2)
        
        tree2 = Tree()
        tree2.add_entry('100644', 'blob', blob2_hash, 'file.txt')
        tree2_hash = remote_repo.write_object(tree2)
        
        commit2 = Commit.create(
            tree_hash=tree2_hash,
            parent_hashes=[commit1_hash],
            author='Test <test@test.com>',
            committer='Test <test@test.com>',
            message='Second commit'
        )
        commit2_hash = remote_repo.write_object(commit2)
        
        (remote_repo.lit_dir / 'refs' / 'heads' / 'main').write_text(commit2_hash + '\n')
        
        # Second fetch
        local_repo.remote.fetch('origin')
        
        # Check remote ref updated
        remote_main = local_repo.remotes_dir / 'origin' / 'main'
        assert remote_main.read_text().strip() == commit2_hash
        
        # Check new commit was fetched
        assert local_repo.object_exists(commit2_hash)
