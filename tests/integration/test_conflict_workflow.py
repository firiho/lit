"""Tests for merge conflict resolution workflow."""

import pytest
from pathlib import Path

from lit.core.repository import Repository
from lit.core.objects import Commit, Tree, Blob
from lit.operations.merge import MergeEngine, MergeResult, MergeConflict


class TestMergeConflictState:
    """Tests for merge state management during conflicts."""
    
    @pytest.fixture
    def repo_with_conflict(self, tmp_path):
        """Create a repository with a merge conflict scenario."""
        repo = Repository(str(tmp_path))
        repo.init()
        merge_engine = MergeEngine(repo)
        
        # Create base commit
        base_blob = Blob(b'base content\n')
        base_blob_hash = repo.write_object(base_blob)
        
        base_tree = Tree()
        base_tree.add_entry('100644', 'blob', base_blob_hash, 'file.txt')
        base_tree_hash = repo.write_object(base_tree)
        
        base_commit = Commit.create(
            tree_hash=base_tree_hash,
            parent_hashes=[],
            author='Test <test@test.com>',
            committer='Test <test@test.com>',
            message='Base commit'
        )
        base_hash = repo.write_object(base_commit)
        
        # Create main branch commit (modifies file)
        main_blob = Blob(b'main content\n')
        main_blob_hash = repo.write_object(main_blob)
        
        main_tree = Tree()
        main_tree.add_entry('100644', 'blob', main_blob_hash, 'file.txt')
        main_tree_hash = repo.write_object(main_tree)
        
        main_commit = Commit.create(
            tree_hash=main_tree_hash,
            parent_hashes=[base_hash],
            author='Test <test@test.com>',
            committer='Test <test@test.com>',
            message='Main commit'
        )
        main_hash = repo.write_object(main_commit)
        
        # Create feature branch commit (also modifies file differently)
        feature_blob = Blob(b'feature content\n')
        feature_blob_hash = repo.write_object(feature_blob)
        
        feature_tree = Tree()
        feature_tree.add_entry('100644', 'blob', feature_blob_hash, 'file.txt')
        feature_tree_hash = repo.write_object(feature_tree)
        
        feature_commit = Commit.create(
            tree_hash=feature_tree_hash,
            parent_hashes=[base_hash],
            author='Test <test@test.com>',
            committer='Test <test@test.com>',
            message='Feature commit'
        )
        feature_hash = repo.write_object(feature_commit)
        
        # Set up branches
        (repo.lit_dir / 'refs' / 'heads' / 'main').write_text(main_hash + '\n')
        (repo.lit_dir / 'refs' / 'heads' / 'feature').write_text(feature_hash + '\n')
        repo.head_file.write_text('ref: refs/heads/main\n')
        
        # Write main file to working tree
        (tmp_path / 'file.txt').write_text('main content\n')
        
        return repo, base_hash, main_hash, feature_hash
    
    def test_save_merge_state(self, repo_with_conflict):
        """Test that merge state is saved correctly."""
        repo, base_hash, main_hash, feature_hash = repo_with_conflict
        merge_engine = MergeEngine(repo)
        
        conflicts = [
            MergeConflict(
                path='file.txt',
                base_content=b'base',
                ours_content=b'ours',
                theirs_content=b'theirs'
            )
        ]
        
        merge_engine.save_merge_state(feature_hash, conflicts)
        
        # Check MERGE_HEAD exists
        merge_head_file = repo.lit_dir / 'MERGE_HEAD'
        assert merge_head_file.exists()
        assert merge_head_file.read_text().strip() == feature_hash
        
        # Check MERGE_MODE exists
        assert (repo.lit_dir / 'MERGE_MODE').exists()
        
        # Check MERGE_MSG exists
        assert (repo.lit_dir / 'MERGE_MSG').exists()
    
    def test_is_merge_in_progress(self, repo_with_conflict):
        """Test detection of ongoing merge."""
        repo, base_hash, main_hash, feature_hash = repo_with_conflict
        merge_engine = MergeEngine(repo)
        
        # Initially no merge
        assert not merge_engine.is_merge_in_progress()
        
        # Save merge state
        merge_engine.save_merge_state(feature_hash, [])
        
        # Now merge is in progress
        assert merge_engine.is_merge_in_progress()
    
    def test_get_merge_head(self, repo_with_conflict):
        """Test getting MERGE_HEAD."""
        repo, base_hash, main_hash, feature_hash = repo_with_conflict
        merge_engine = MergeEngine(repo)
        
        # No merge head initially
        assert merge_engine.get_merge_head() is None
        
        # Save merge state
        merge_engine.save_merge_state(feature_hash, [])
        
        # Now should return the hash
        assert merge_engine.get_merge_head() == feature_hash
    
    def test_clear_merge_state(self, repo_with_conflict):
        """Test clearing merge state."""
        repo, base_hash, main_hash, feature_hash = repo_with_conflict
        merge_engine = MergeEngine(repo)
        
        # Save merge state
        merge_engine.save_merge_state(feature_hash, [])
        assert merge_engine.is_merge_in_progress()
        
        # Clear it
        merge_engine.clear_merge_state()
        
        # Should no longer be in progress
        assert not merge_engine.is_merge_in_progress()
        assert not (repo.lit_dir / 'MERGE_HEAD').exists()
    
    def test_abort_merge(self, repo_with_conflict, tmp_path):
        """Test aborting a merge."""
        repo, base_hash, main_hash, feature_hash = repo_with_conflict
        merge_engine = MergeEngine(repo)
        
        # Simulate merge in progress with modified working tree
        merge_engine.save_merge_state(feature_hash, [])
        (tmp_path / 'file.txt').write_text('conflict markers here')
        
        # Abort
        result = merge_engine.abort_merge()
        
        assert result is True
        assert not merge_engine.is_merge_in_progress()


class TestConflictMarkers:
    """Tests for conflict marker generation and detection."""
    
    def test_generate_conflict_markers(self, tmp_path):
        """Test generating conflict markers."""
        repo = Repository(str(tmp_path))
        repo.init()
        merge_engine = MergeEngine(repo)
        
        markers = merge_engine.generate_conflict_markers(
            path='file.txt',
            ours_content=b'our line\n',
            theirs_content=b'their line\n'
        )
        
        content = markers.decode('utf-8')
        assert '<<<<<<< HEAD' in content
        assert 'our line' in content
        assert '=======' in content
        assert 'their line' in content
        assert '>>>>>>>' in content
    
    def test_write_conflicts_to_working_tree(self, tmp_path):
        """Test writing conflict markers to working tree files."""
        repo = Repository(str(tmp_path))
        repo.init()
        merge_engine = MergeEngine(repo)
        
        conflicts = [
            MergeConflict(
                path='file.txt',
                base_content=b'base\n',
                ours_content=b'ours\n',
                theirs_content=b'theirs\n'
            )
        ]
        
        merge_engine.write_conflicts_to_working_tree(conflicts)
        
        file_path = tmp_path / 'file.txt'
        assert file_path.exists()
        
        content = file_path.read_text()
        assert '<<<<<<< HEAD' in content
        assert '=======' in content


class TestAddDuringMerge:
    """Tests for 'lit add' behavior during merge conflicts."""
    
    def test_has_conflict_markers(self, tmp_path):
        """Test detection of conflict markers in files."""
        from lit.cli.commands.add import has_conflict_markers
        
        # File with conflict markers
        conflict_file = tmp_path / 'conflict.txt'
        conflict_file.write_text('<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>>\n')
        
        assert has_conflict_markers(conflict_file) is True
        
        # File without conflict markers
        clean_file = tmp_path / 'clean.txt'
        clean_file.write_text('normal content\n')
        
        assert has_conflict_markers(clean_file) is False
    
    def test_has_conflict_markers_partial(self, tmp_path):
        """Test detection with only some conflict markers."""
        from lit.cli.commands.add import has_conflict_markers
        
        # File with just HEAD marker (still counts as conflict)
        file1 = tmp_path / 'partial1.txt'
        file1.write_text('before\n<<<<<<< HEAD\nafter\n')
        
        assert has_conflict_markers(file1) is True
        
        # File with just ======= (also counts)
        file2 = tmp_path / 'partial2.txt'
        file2.write_text('before\n=======\nafter\n')
        
        assert has_conflict_markers(file2) is True


class TestMergeCommit:
    """Tests for creating merge commits."""
    
    def test_commit_with_merge_head(self, tmp_path):
        """Test that commit detects MERGE_HEAD and creates merge commit."""
        repo = Repository(str(tmp_path))
        repo.init()
        
        # Create two commits to have parents
        blob = Blob(b'content')
        blob_hash = repo.write_object(blob)
        
        tree = Tree()
        tree.add_entry('100644', 'blob', blob_hash, 'file.txt')
        tree_hash = repo.write_object(tree)
        
        commit1 = Commit.create(
            tree_hash=tree_hash,
            parent_hashes=[],
            author='Test <test@test.com>',
            committer='Test <test@test.com>',
            message='First'
        )
        commit1_hash = repo.write_object(commit1)
        
        commit2 = Commit.create(
            tree_hash=tree_hash,
            parent_hashes=[],
            author='Test <test@test.com>',
            committer='Test <test@test.com>',
            message='Second'
        )
        commit2_hash = repo.write_object(commit2)
        
        # Set up HEAD on commit1
        (repo.lit_dir / 'refs' / 'heads' / 'main').write_text(commit1_hash + '\n')
        repo.head_file.write_text('ref: refs/heads/main\n')
        
        # Create MERGE_HEAD pointing to commit2
        (repo.lit_dir / 'MERGE_HEAD').write_text(commit2_hash + '\n')
        
        # Verify merge is in progress
        merge_engine = MergeEngine(repo)
        assert merge_engine.is_merge_in_progress()
        assert merge_engine.get_merge_head() == commit2_hash
