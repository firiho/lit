"""Integration tests for rebase workflow."""

import os
import pytest
from click.testing import CliRunner

from lit.cli.main import cli


@pytest.fixture
def runner():
    """Create CLI runner."""
    return CliRunner()


@pytest.fixture
def initialized_repo(runner, tmp_path):
    """Create an initialized repository with config."""
    os.chdir(tmp_path)
    runner.invoke(cli, ["init"])
    runner.invoke(cli, ["config", "set", "user.name", "Test User"])
    runner.invoke(cli, ["config", "set", "user.email", "test@test.com"])
    return tmp_path


class TestRebaseBasic:
    """Test basic rebase functionality."""

    def test_rebase_no_repo(self, runner, tmp_path):
        """Test rebase fails outside repository."""
        os.chdir(tmp_path)
        result = runner.invoke(cli, ["rebase", "main"])
        assert result.exit_code != 0 or "Not a lit repository" in result.output or "no such ref" in result.output.lower()

    def test_rebase_no_upstream(self, runner, initialized_repo):
        """Test rebase without upstream argument."""
        result = runner.invoke(cli, ["rebase"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "UPSTREAM" in result.output

    def test_rebase_invalid_upstream(self, runner, initialized_repo):
        """Test rebase with invalid upstream ref."""
        # Create initial commit
        test_file = initialized_repo / "file.txt"
        test_file.write_text("content")
        runner.invoke(cli, ["add", "file.txt"])
        runner.invoke(cli, ["commit", "-m", "Initial"])

        result = runner.invoke(cli, ["rebase", "nonexistent"])
        assert result.exit_code != 0 or "not a valid" in result.output.lower() or "not found" in result.output.lower()

    def test_rebase_linear_history(self, runner, initialized_repo):
        """Test rebase with linear history (no-op)."""
        # Create commits
        test_file = initialized_repo / "file.txt"
        test_file.write_text("Initial")
        runner.invoke(cli, ["add", "file.txt"])
        runner.invoke(cli, ["commit", "-m", "Initial"])

        test_file.write_text("Second")
        runner.invoke(cli, ["add", "file.txt"])
        runner.invoke(cli, ["commit", "-m", "Second"])

        # Create branch at current position
        runner.invoke(cli, ["branch", "feature"])
        runner.invoke(cli, ["switch", "feature"])

        # Add feature commit
        test_file.write_text("Feature")
        runner.invoke(cli, ["add", "file.txt"])
        runner.invoke(cli, ["commit", "-m", "Feature"])

        # Rebase onto main (should be no-op since feature is already on main)
        result = runner.invoke(cli, ["rebase", "main"])
        assert result.exit_code == 0
        # Either "Nothing to rebase" or "Rebase complete" with 0 commits
        assert "rebase" in result.output.lower() or "nothing" in result.output.lower() or "complete" in result.output.lower()


class TestRebaseDivergentBranches:
    """Test rebase with divergent branches."""

    def test_rebase_feature_onto_main(self, runner, initialized_repo):
        """Test rebasing feature branch onto updated main."""
        # Initial commit
        test_file = initialized_repo / "file.txt"
        test_file.write_text("Initial")
        runner.invoke(cli, ["add", "file.txt"])
        commit_result = runner.invoke(cli, ["commit", "-m", "Initial"])

        # Get initial commit hash (split()[1] to skip the '*' prefix)
        log_result = runner.invoke(cli, ["log", "--oneline"])
        initial_hash = log_result.output.strip().split()[1][:7]

        # Add main commit
        test_file.write_text("Initial\nMain change")
        runner.invoke(cli, ["add", "file.txt"])
        runner.invoke(cli, ["commit", "-m", "Main commit"])

        # Create feature branch from initial commit
        runner.invoke(cli, ["branch", "feature", initial_hash])
        runner.invoke(cli, ["switch", "feature"])

        # Add feature file (different file to avoid conflicts)
        feature_file = initialized_repo / "feature.txt"
        feature_file.write_text("Feature content")
        runner.invoke(cli, ["add", "feature.txt"])
        runner.invoke(cli, ["commit", "-m", "Feature commit"])

        # Rebase feature onto main
        result = runner.invoke(cli, ["rebase", "main"])
        assert result.exit_code == 0
        assert "Rebase complete" in result.output or "Rebasing" in result.output

        # Verify feature.txt still exists
        assert feature_file.exists()

        # Verify history is linear
        log_result = runner.invoke(cli, ["log"])
        assert "Feature commit" in log_result.output
        assert "Main commit" in log_result.output

    def test_rebase_multiple_commits(self, runner, initialized_repo):
        """Test rebasing multiple commits."""
        # Initial commit
        test_file = initialized_repo / "file.txt"
        test_file.write_text("Initial")
        runner.invoke(cli, ["add", "file.txt"])
        runner.invoke(cli, ["commit", "-m", "Initial"])

        log_result = runner.invoke(cli, ["log", "--oneline"])
        initial_hash = log_result.output.strip().split()[1][:7]

        # Main commit
        test_file.write_text("Main")
        runner.invoke(cli, ["add", "file.txt"])
        runner.invoke(cli, ["commit", "-m", "Main"])

        # Create feature branch
        runner.invoke(cli, ["branch", "feature", initial_hash])
        runner.invoke(cli, ["switch", "feature"])

        # Multiple feature commits
        for i in range(3):
            f = initialized_repo / f"feature{i}.txt"
            f.write_text(f"Feature {i}")
            runner.invoke(cli, ["add", f"feature{i}.txt"])
            runner.invoke(cli, ["commit", "-m", f"Feature commit {i}"])

        # Rebase
        result = runner.invoke(cli, ["rebase", "main"])
        assert result.exit_code == 0
        assert "3 commit" in result.output or "Rebase complete" in result.output

        # Verify all files exist
        for i in range(3):
            assert (initialized_repo / f"feature{i}.txt").exists()


class TestRebaseAbort:
    """Test rebase --abort functionality."""

    def test_abort_no_rebase(self, runner, initialized_repo):
        """Test abort when no rebase in progress."""
        result = runner.invoke(cli, ["rebase", "--abort"])
        assert "No rebase in progress" in result.output

    def test_abort_cleans_state(self, runner, initialized_repo):
        """Test that abort cleans up rebase state directory."""
        # Setup repo with commits
        test_file = initialized_repo / "file.txt"
        test_file.write_text("Initial")
        runner.invoke(cli, ["add", "file.txt"])
        runner.invoke(cli, ["commit", "-m", "Initial"])

        # Check no rebase state exists
        rebase_dir = initialized_repo / ".lit" / "rebase-apply"
        assert not rebase_dir.exists()

        # Try abort (should say no rebase)
        result = runner.invoke(cli, ["rebase", "--abort"])
        assert "No rebase in progress" in result.output


class TestRebaseSkip:
    """Test rebase --skip functionality."""

    def test_skip_no_rebase(self, runner, initialized_repo):
        """Test skip when no rebase in progress."""
        result = runner.invoke(cli, ["rebase", "--skip"])
        assert "No rebase in progress" in result.output


class TestRebaseContinue:
    """Test rebase --continue functionality."""

    def test_continue_no_rebase(self, runner, initialized_repo):
        """Test continue when no rebase in progress."""
        result = runner.invoke(cli, ["rebase", "--continue"])
        assert "No rebase in progress" in result.output


class TestRebaseInteractive:
    """Test rebase -i/--interactive flag."""

    def test_interactive_flag_recognized(self, runner, initialized_repo):
        """Test that -i flag is recognized."""
        test_file = initialized_repo / "file.txt"
        test_file.write_text("content")
        runner.invoke(cli, ["add", "file.txt"])
        runner.invoke(cli, ["commit", "-m", "Initial"])

        # Interactive rebase should be recognized (even if not fully implemented)
        result = runner.invoke(cli, ["rebase", "-i", "HEAD"])
        # Should either work or show a message about interactive mode
        assert result.exit_code == 0 or "interactive" in result.output.lower()


class TestRebaseEdgeCases:
    """Test edge cases for rebase."""

    def test_rebase_current_branch(self, runner, initialized_repo):
        """Test rebasing onto current HEAD."""
        test_file = initialized_repo / "file.txt"
        test_file.write_text("content")
        runner.invoke(cli, ["add", "file.txt"])
        runner.invoke(cli, ["commit", "-m", "Initial"])

        result = runner.invoke(cli, ["rebase", "HEAD"])
        # Should handle gracefully
        assert result.exit_code == 0 or "Nothing to rebase" in result.output or "Already up to date" in result.output or "0 commit" in result.output

    def test_rebase_preserves_commit_messages(self, runner, initialized_repo):
        """Test that commit messages are preserved during rebase."""
        test_file = initialized_repo / "file.txt"
        test_file.write_text("Initial")
        runner.invoke(cli, ["add", "file.txt"])
        runner.invoke(cli, ["commit", "-m", "Initial"])

        log_result = runner.invoke(cli, ["log", "--oneline"])
        initial_hash = log_result.output.strip().split()[1][:7]

        test_file.write_text("Main")
        runner.invoke(cli, ["add", "file.txt"])
        runner.invoke(cli, ["commit", "-m", "Main"])

        runner.invoke(cli, ["branch", "feature", initial_hash])
        runner.invoke(cli, ["switch", "feature"])

        feature_file = initialized_repo / "feature.txt"
        feature_file.write_text("Feature content")
        runner.invoke(cli, ["add", "feature.txt"])
        runner.invoke(cli, ["commit", "-m", "My special feature message"])

        runner.invoke(cli, ["rebase", "main"])

        log_result = runner.invoke(cli, ["log"])
        assert "My special feature message" in log_result.output
