"""Unit tests for remote repository operations."""

import pytest
from pathlib import Path
from lit.core.repository import Repository
from lit.remote.remote import RemoteManager
from lit.core.objects import Commit, Tree, Blob
from lit.core.index import Index
from tests.conftest import make_commit


def test_remote_manager_initialization(repo):
    """Test RemoteManager initialization."""
    remote = repo.remote
    assert isinstance(remote, RemoteManager)
    assert remote.repo == repo


def test_add_remote(repo):
    """Test adding a remote repository."""
    remote_url = "/path/to/remote"
    repo.remote.add_remote("origin", remote_url)
    
    # Verify remote was added to config
    remotes = repo.remote.list_remotes()
    assert "origin" in remotes
    assert remotes["origin"] == remote_url


def test_add_multiple_remotes(repo):
    """Test adding multiple remotes."""
    repo.remote.add_remote("origin", "/path/to/origin")
    repo.remote.add_remote("upstream", "/path/to/upstream")
    
    remotes = repo.remote.list_remotes()
    assert len(remotes) == 2
    assert remotes["origin"] == "/path/to/origin"
    assert remotes["upstream"] == "/path/to/upstream"


def test_get_remote_url(repo):
    """Test getting remote URL."""
    repo.remote.add_remote("origin", "/path/to/remote")
    
    url = repo.remote.get_remote_url("origin")
    assert url == "/path/to/remote"


def test_get_nonexistent_remote_url(repo):
    """Test getting URL for non-existent remote."""
    url = repo.remote.get_remote_url("nonexistent")
    assert url is None


def test_list_remotes_empty(repo):
    """Test listing remotes when none exist."""
    remotes = repo.remote.list_remotes()
    assert remotes == {}


def test_remove_remote(repo):
    """Test removing a remote."""
    repo.remote.add_remote("origin", "/path/to/remote")
    assert "origin" in repo.remote.list_remotes()
    
    repo.remote.remove_remote("origin")
    assert "origin" not in repo.remote.list_remotes()


def test_remove_nonexistent_remote(repo):
    """Test removing non-existent remote doesn't error."""
    # Should not raise an exception
    repo.remote.remove_remote("nonexistent")


def test_parse_url_file_protocol(repo):
    """Test URL parsing for file:// protocol."""
    protocol, path = repo.remote._parse_url("file:///path/to/repo")
    assert protocol == "file"
    assert path == "/path/to/repo"


def test_parse_url_https_protocol(repo):
    """Test URL parsing for https:// protocol."""
    protocol, path = repo.remote._parse_url("https://github.com/user/repo.git")
    assert protocol == "https"
    assert path == "github.com/user/repo.git"


def test_parse_url_ssh_protocol(repo):
    """Test URL parsing for ssh:// protocol."""
    protocol, path = repo.remote._parse_url("ssh://git@github.com/user/repo.git")
    assert protocol == "ssh"
    assert path == "git@github.com/user/repo.git"


def test_parse_url_git_ssh_format(repo):
    """Test URL parsing for git@host:repo format."""
    protocol, path = repo.remote._parse_url("git@github.com:user/repo.git")
    assert protocol == "ssh"
    assert path == "git@github.com:user/repo.git"


def test_parse_url_local_path(repo):
    """Test URL parsing for local file path."""
    protocol, path = repo.remote._parse_url("/path/to/repo")
    assert protocol == "file"
    assert path == "/path/to/repo"


def test_parse_url_relative_path(repo):
    """Test URL parsing for relative path."""
    protocol, path = repo.remote._parse_url("../other-repo")
    assert protocol == "file"
    assert path == "../other-repo"


def test_clone_creates_destination(temp_dir, repo_with_commits):
    """Test that clone creates destination directory."""
    source = repo_with_commits
    dest_path = temp_dir / "cloned"
    
    # Clone the repository
    temp_repo = Repository(str(temp_dir))
    cloned = temp_repo.remote.clone(str(source.work_tree), str(dest_path))
    
    assert dest_path.exists()
    assert (dest_path / ".lit").exists()


def test_clone_copies_objects(temp_dir, repo_with_commits):
    """Test that clone copies all objects."""
    source = repo_with_commits
    dest_path = temp_dir / "cloned"
    
    # Get object count from source
    source_objects = list(source.objects_dir.rglob("*"))
    source_object_count = len([f for f in source_objects if f.is_file()])
    
    # Clone
    temp_repo = Repository(str(temp_dir))
    cloned = temp_repo.remote.clone(str(source.work_tree), str(dest_path))
    
    # Count objects in cloned repo
    cloned_objects = list(cloned.objects_dir.rglob("*"))
    cloned_object_count = len([f for f in cloned_objects if f.is_file()])
    
    assert cloned_object_count == source_object_count


def test_clone_sets_up_remote(temp_dir, repo_with_commits):
    """Test that clone sets up origin remote."""
    source = repo_with_commits
    dest_path = temp_dir / "cloned"
    
    temp_repo = Repository(str(temp_dir))
    cloned = temp_repo.remote.clone(str(source.work_tree), str(dest_path))
    
    remotes = cloned.remote.list_remotes()
    assert "origin" in remotes
    assert Path(remotes["origin"]) == source.work_tree


def test_clone_checks_out_default_branch(temp_dir, repo_with_commits):
    """Test that clone checks out the default branch."""
    source = repo_with_commits
    dest_path = temp_dir / "cloned"
    
    temp_repo = Repository(str(temp_dir))
    cloned = temp_repo.remote.clone(str(source.work_tree), str(dest_path))
    
    # Check HEAD points to main
    head_content = cloned.head_file.read_text().strip()
    assert head_content == "ref: refs/heads/main"
    
    # Check files were checked out
    assert (dest_path / "file1.txt").exists()
    assert (dest_path / "file2.txt").exists()


def test_clone_copies_branches(temp_dir, repo_with_commits):
    """Test that clone copies branch references."""
    source = repo_with_commits
    
    # Create a feature branch in source
    current_commit = source.refs.resolve_head()
    source.refs.create_branch("feature", current_commit)
    
    dest_path = temp_dir / "cloned"
    temp_repo = Repository(str(temp_dir))
    cloned = temp_repo.remote.clone(str(source.work_tree), str(dest_path))
    
    # Check remote tracking branches exist
    assert (cloned.remotes_dir / "origin" / "main").exists()
    assert (cloned.remotes_dir / "origin" / "feature").exists()


def test_clone_fails_with_existing_destination(temp_dir, repo_with_commits):
    """Test that clone fails if destination exists."""
    source = repo_with_commits
    dest_path = temp_dir / "cloned"
    dest_path.mkdir()
    
    temp_repo = Repository(str(temp_dir))
    with pytest.raises(Exception, match="Destination already exists"):
        temp_repo.remote.clone(str(source.work_tree), str(dest_path))


def test_clone_fails_with_invalid_source(temp_dir):
    """Test that clone fails if source doesn't exist."""
    dest_path = temp_dir / "cloned"
    
    temp_repo = Repository(str(temp_dir))
    with pytest.raises(Exception, match="Source repository not found"):
        temp_repo.remote.clone("/nonexistent/path", str(dest_path))


def test_clone_fails_with_non_repo_source(temp_dir):
    """Test that clone fails if source is not a repository."""
    source_path = temp_dir / "not-a-repo"
    source_path.mkdir()
    dest_path = temp_dir / "cloned"
    
    temp_repo = Repository(str(temp_dir))
    with pytest.raises(Exception, match="Not a valid lit repository"):
        temp_repo.remote.clone(str(source_path), str(dest_path))


def test_fetch_updates_remote_tracking_branches(temp_dir, repo_with_commits):
    """Test that fetch updates remote tracking branches."""
    source = repo_with_commits
    dest_path = temp_dir / "cloned"
    
    # Clone
    temp_repo = Repository(str(temp_dir))
    cloned = temp_repo.remote.clone(str(source.work_tree), str(dest_path))
    
    # Get initial commit
    initial_commit = (cloned.remotes_dir / "origin" / "main").read_text().strip()
    
    # Make a new commit in source
    file3 = source.work_tree / "file3.txt"
    file3.write_text("New content")
    source.index.add_file(source, file3)
    new_commit = make_commit(source, "Add file3")
    
    # Fetch from origin
    cloned.remote.fetch("origin")
    
    # Check remote tracking branch was updated
    updated_commit = (cloned.remotes_dir / "origin" / "main").read_text().strip()
    assert updated_commit == new_commit
    assert updated_commit != initial_commit


def test_fetch_copies_new_objects(temp_dir, repo_with_commits):
    """Test that fetch copies new objects."""
    source = repo_with_commits
    dest_path = temp_dir / "cloned"
    
    # Clone
    temp_repo = Repository(str(temp_dir))
    cloned = temp_repo.remote.clone(str(source.work_tree), str(dest_path))
    
    # Count initial objects
    initial_objects = list(cloned.objects_dir.rglob("*"))
    initial_count = len([f for f in initial_objects if f.is_file()])
    
    # Make new commit in source
    file3 = source.work_tree / "file3.txt"
    file3.write_text("New content")
    source.index.add_file(source, file3)
    make_commit(source, "Add file3")
    
    # Fetch
    cloned.remote.fetch("origin")
    
    # Count objects after fetch
    after_objects = list(cloned.objects_dir.rglob("*"))
    after_count = len([f for f in after_objects if f.is_file()])
    
    assert after_count > initial_count


def test_fetch_specific_branch(temp_dir, repo_with_commits):
    """Test fetching a specific branch."""
    source = repo_with_commits
    
    # Create feature branch
    current_commit = source.refs.resolve_head()
    source.refs.create_branch("feature", current_commit)
    
    dest_path = temp_dir / "cloned"
    temp_repo = Repository(str(temp_dir))
    cloned = temp_repo.remote.clone(str(source.work_tree), str(dest_path))
    
    # Make commit on feature branch in source
    source.refs.set_head("feature")
    file3 = source.work_tree / "file3.txt"
    file3.write_text("Feature content")
    source.index.add_file(source, file3)
    feature_commit = make_commit(source, "Feature work")
    
    # Fetch only feature branch
    cloned.remote.fetch("origin", "feature")
    
    # Check feature branch was updated
    feature_ref = (cloned.remotes_dir / "origin" / "feature").read_text().strip()
    assert feature_ref == feature_commit


def test_fetch_fails_with_invalid_remote(repo):
    """Test that fetch fails with non-existent remote."""
    with pytest.raises(Exception, match="Remote .* not found"):
        repo.remote.fetch("nonexistent")


def test_push_updates_remote_branch(temp_dir, repo_with_commits):
    """Test that push updates remote branch reference."""
    source = repo_with_commits
    dest_path = temp_dir / "cloned"
    
    # Clone
    temp_repo = Repository(str(temp_dir))
    cloned = temp_repo.remote.clone(str(source.work_tree), str(dest_path))
    
    # Make new commit in cloned repo
    index = Index()
    index.read(str(cloned.index_file))
    file3 = cloned.work_tree / "file3.txt"
    file3.write_text("New content")
    index.add_file(cloned, file3)
    cloned.index = index  # Set index so make_commit uses it
    new_commit = make_commit(cloned, "Add file3")
    
    # Push to origin
    cloned.remote.push("origin")
    
    # Check source repo was updated
    source_main = (source.heads_dir / "main").read_text().strip()
    assert source_main == new_commit


def test_push_copies_objects(temp_dir, repo_with_commits):
    """Test that push copies objects to remote."""
    source = repo_with_commits
    dest_path = temp_dir / "cloned"
    
    # Clone
    temp_repo = Repository(str(temp_dir))
    cloned = temp_repo.remote.clone(str(source.work_tree), str(dest_path))
    
    # Count objects in source
    initial_objects = list(source.objects_dir.rglob("*"))
    initial_count = len([f for f in initial_objects if f.is_file()])
    
    # Make new commit in cloned
    index = Index()
    index.read(str(cloned.index_file))
    file3 = cloned.work_tree / "file3.txt"
    file3.write_text("New content")
    index.add_file(cloned, file3)
    cloned.index = index  # Set index so make_commit uses it
    make_commit(cloned, "Add file3")
    
    # Push
    cloned.remote.push("origin")
    
    # Count objects in source after push
    after_objects = list(source.objects_dir.rglob("*"))
    after_count = len([f for f in after_objects if f.is_file()])
    
    assert after_count > initial_count


def test_push_specific_branch(temp_dir, repo_with_commits):
    """Test pushing a specific branch."""
    source = repo_with_commits
    dest_path = temp_dir / "cloned"
    
    # Clone
    temp_repo = Repository(str(temp_dir))
    cloned = temp_repo.remote.clone(str(source.work_tree), str(dest_path))
    
    # Create feature branch in cloned
    current_commit = cloned.refs.resolve_head()
    cloned.refs.create_branch("feature", current_commit)
    cloned.refs.set_head("feature")
    
    # Make commit on feature
    index = Index()
    index.read(str(cloned.index_file))
    file3 = cloned.work_tree / "file3.txt"
    file3.write_text("Feature content")
    index.add_file(cloned, file3)
    cloned.index = index  # Set index so make_commit uses it
    feature_commit = make_commit(cloned, "Feature work")
    
    # Push feature branch
    cloned.remote.push("origin", "feature")
    
    # Check feature branch exists in source
    source_feature = (source.heads_dir / "feature").read_text().strip()
    assert source_feature == feature_commit


def test_push_fails_with_invalid_remote(repo):
    """Test that push fails with non-existent remote."""
    with pytest.raises(Exception, match="Remote .* not found"):
        repo.remote.push("nonexistent")


def test_push_fails_from_detached_head(temp_dir, repo_with_commits):
    """Test that push fails from detached HEAD."""
    source = repo_with_commits
    dest_path = temp_dir / "cloned"
    
    temp_repo = Repository(str(temp_dir))
    cloned = temp_repo.remote.clone(str(source.work_tree), str(dest_path))
    
    # Detach HEAD
    commit_hash = cloned.refs.resolve_head()
    if commit_hash:  # Only detach if we have a commit
        cloned.head_file.write_text(commit_hash + "\n")
        
        with pytest.raises(Exception, match="Cannot push from detached HEAD"):
            cloned.remote.push("origin")


def test_push_fails_with_nonexistent_branch(temp_dir, repo_with_commits):
    """Test that push fails with non-existent branch."""
    source = repo_with_commits
    dest_path = temp_dir / "cloned"
    
    temp_repo = Repository(str(temp_dir))
    cloned = temp_repo.remote.clone(str(source.work_tree), str(dest_path))
    
    with pytest.raises(Exception, match="Branch .* not found"):
        cloned.remote.push("origin", "nonexistent")


def test_clone_with_file_protocol(temp_dir, repo_with_commits):
    """Test cloning with file:// protocol."""
    source = repo_with_commits
    dest_path = temp_dir / "cloned"
    
    temp_repo = Repository(str(temp_dir))
    cloned = temp_repo.remote.clone(f"file://{source.work_tree}", str(dest_path))
    
    # Compare resolved paths
    assert cloned.work_tree.resolve() == dest_path.resolve()
    assert (dest_path / "file1.txt").exists()


def test_clone_with_unsupported_protocol(temp_dir):
    """Test that clone fails with unsupported protocol."""
    dest_path = temp_dir / "cloned"
    
    temp_repo = Repository(str(temp_dir))
    with pytest.raises(NotImplementedError, match="Protocol .* not yet implemented"):
        temp_repo.remote.clone("https://github.com/user/repo.git", str(dest_path))


def test_fetch_with_unsupported_protocol(repo):
    """Test that fetch fails with unsupported protocol."""
    repo.remote.add_remote("origin", "https://github.com/user/repo.git")
    
    with pytest.raises(NotImplementedError, match="Protocol .* not yet implemented"):
        repo.remote.fetch("origin")


def test_push_with_unsupported_protocol(repo):
    """Test that push fails with unsupported protocol."""
    repo.remote.add_remote("origin", "https://github.com/user/repo.git")
    
    # Create a dummy branch
    (repo.heads_dir / "main").write_text("abc123\n")
    repo.head_file.write_text("ref: refs/heads/main\n")
    
    with pytest.raises(NotImplementedError, match="Protocol .* not yet implemented"):
        repo.remote.push("origin")


def test_remote_tracking_branch_format(temp_dir, repo_with_commits):
    """Test that remote tracking branches are stored correctly."""
    source = repo_with_commits
    dest_path = temp_dir / "cloned"
    
    temp_repo = Repository(str(temp_dir))
    cloned = temp_repo.remote.clone(str(source.work_tree), str(dest_path))
    
    # Check refs/remotes/origin structure
    assert (cloned.refs_dir / "remotes" / "origin").exists()
    assert (cloned.remotes_dir / "origin" / "main").exists()
    
    # Verify it points to same commit as source
    source_commit = (source.heads_dir / "main").read_text().strip()
    cloned_tracking = (cloned.remotes_dir / "origin" / "main").read_text().strip()
    assert cloned_tracking == source_commit


def test_config_fetch_refspec(repo):
    """Test that remote config includes fetch refspec."""
    repo.remote.add_remote("origin", "/path/to/remote")
    
    # Read config file
    config_content = repo.config_file.read_text()
    assert '[remote "origin"]' in config_content
    assert "fetch = +refs/heads/*:refs/remotes/origin/*" in config_content


def test_clone_bare_repository(temp_dir, repo_with_commits):
    """Test cloning a bare repository."""
    source = repo_with_commits
    dest_path = temp_dir / "bare_repo.git"
    
    temp_repo = Repository(str(temp_dir))
    bare_repo = temp_repo.remote.clone(str(source.work_tree), str(dest_path), bare=True)
    
    # Bare repo should exist
    assert bare_repo.lit_dir.exists()
    
    # Should NOT have working directory files
    assert not (dest_path / "test.txt").exists()
    
    # Should have branches in heads/ not remotes/
    assert (bare_repo.heads_dir / "main").exists()
    assert not (bare_repo.remotes_dir / "origin").exists()
    
    # Should NOT have remote config
    config_content = bare_repo.config_file.read_text()
    assert '[remote "origin"]' not in config_content
    
    # Should have all objects
    source_commit_hash = (source.heads_dir / "main").read_text().strip()
    bare_commit_hash = (bare_repo.heads_dir / "main").read_text().strip()
    assert source_commit_hash == bare_commit_hash


def test_clone_bare_creates_git_suffix(temp_dir, repo_with_commits):
    """Test that bare clone works with .git suffix."""
    source = repo_with_commits
    dest_path = temp_dir / "origin.git"
    
    temp_repo = Repository(str(temp_dir))
    bare_repo = temp_repo.remote.clone(str(source.work_tree), str(dest_path), bare=True)
    
    assert dest_path.exists()
    assert bare_repo.lit_dir.exists()
    
    # Should have branches in heads/
    assert (bare_repo.heads_dir / "main").exists()


def test_clone_regular_from_bare(temp_dir, repo_with_commits):
    """Test cloning a regular repo from a bare repo."""
    source = repo_with_commits
    
    # First create a bare repo
    bare_path = temp_dir / "bare.git"
    temp_repo = Repository(str(temp_dir))
    bare_repo = temp_repo.remote.clone(str(source.work_tree), str(bare_path), bare=True)
    
    # Verify bare repo has the objects and branches
    bare_main_hash = (bare_repo.heads_dir / "main").read_text().strip()
    bare_commit = bare_repo.read_object(bare_main_hash)
    assert bare_commit  # Commit should exist
    
    # Now clone a regular repo from the bare one
    dev_path = temp_dir / "dev"
    dev_repo = temp_repo.remote.clone(str(bare_path), str(dev_path), bare=False)
    
    # Dev repo should have working directory files
    assert (dev_repo.work_tree / "file1.txt").exists()
    assert (dev_repo.work_tree / "file2.txt").exists()
    
    # Should have remote tracking branches
    assert (dev_repo.remotes_dir / "origin" / "main").exists()
    
    # Should have origin remote configured
    config_content = dev_repo.config_file.read_text()
    assert '[remote "origin"]' in config_content
