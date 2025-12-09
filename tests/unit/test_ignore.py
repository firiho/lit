"""Tests for ignore pattern matching."""

import pytest
from pathlib import Path

from lit.utils.ignore import IgnorePattern, IgnoreMatcher, get_ignore_matcher


class TestIgnorePattern:
    """Tests for individual ignore patterns."""
    
    def test_simple_pattern(self):
        """Test simple filename pattern."""
        pattern = IgnorePattern("*.log")
        assert pattern.matches("test.log")
        assert pattern.matches("dir/test.log")
        assert not pattern.matches("test.txt")
        assert not pattern.matches("logfile")
    
    def test_directory_pattern(self):
        """Test directory-only pattern."""
        pattern = IgnorePattern("temp", directory_only=True)
        # Should match files inside temp/
        assert pattern.matches("temp/file.txt")
        assert pattern.matches("temp/sub/file.txt")
        # Should match temp itself as a directory
        assert pattern.matches("temp", is_dir=True)
    
    def test_negation_pattern(self):
        """Test negation patterns."""
        pattern = IgnorePattern("*.txt", negation=True)
        assert pattern.matches("test.txt")
        assert pattern.negation is True
    
    def test_double_star_pattern(self):
        """Test ** pattern for any path."""
        pattern = IgnorePattern("**/test.log")
        assert pattern.matches("test.log")
        assert pattern.matches("dir/test.log")
        assert pattern.matches("dir/sub/test.log")
    
    def test_anchored_pattern(self):
        """Test anchored pattern (starts with /)."""
        pattern = IgnorePattern("/root.txt")
        assert pattern.matches("root.txt")
        # Anchored patterns only match at root
        # (Note: actual behavior depends on implementation)
    
    def test_question_mark_pattern(self):
        """Test ? pattern for single character."""
        pattern = IgnorePattern("test?.txt")
        assert pattern.matches("test1.txt")
        assert pattern.matches("testa.txt")
        assert not pattern.matches("test.txt")
        assert not pattern.matches("test12.txt")


class TestIgnoreMatcher:
    """Tests for the IgnoreMatcher class."""
    
    def test_empty_matcher(self):
        """Empty matcher should not ignore anything."""
        matcher = IgnoreMatcher()
        assert not matcher.is_ignored("test.txt")
        assert not matcher.is_ignored("any/path/file.py")
    
    def test_add_pattern(self):
        """Test adding patterns."""
        matcher = IgnoreMatcher()
        matcher.add_pattern("*.log")
        assert matcher.is_ignored("test.log")
        assert not matcher.is_ignored("test.txt")
    
    def test_comments_ignored(self):
        """Comments should be ignored."""
        matcher = IgnoreMatcher()
        matcher.add_pattern("# This is a comment")
        matcher.add_pattern("*.log")
        assert matcher.is_ignored("test.log")
    
    def test_empty_lines_ignored(self):
        """Empty lines should be ignored."""
        matcher = IgnoreMatcher()
        matcher.add_pattern("")
        matcher.add_pattern("   ")
        matcher.add_pattern("*.log")
        assert matcher.is_ignored("test.log")
    
    def test_negation_overrides(self):
        """Negation patterns should un-ignore files."""
        matcher = IgnoreMatcher()
        matcher.add_pattern("*.log")
        matcher.add_pattern("!important.log")
        assert matcher.is_ignored("test.log")
        assert not matcher.is_ignored("important.log")
    
    def test_last_pattern_wins(self):
        """The last matching pattern should win."""
        matcher = IgnoreMatcher()
        matcher.add_pattern("*.log")
        matcher.add_pattern("!*.log")
        matcher.add_pattern("error.log")
        assert matcher.is_ignored("error.log")
        assert not matcher.is_ignored("test.log")
    
    def test_load_file(self, tmp_path):
        """Test loading patterns from file."""
        ignore_file = tmp_path / ".litignore"
        ignore_file.write_text("*.log\n*.tmp\n# Comment\n__pycache__/\n")
        
        matcher = IgnoreMatcher()
        assert matcher.load_file(ignore_file)
        assert matcher.is_ignored("test.log")
        assert matcher.is_ignored("cache.tmp")
        assert matcher.is_ignored("__pycache__/module.pyc")
    
    def test_load_nonexistent_file(self, tmp_path):
        """Loading nonexistent file should return False."""
        matcher = IgnoreMatcher()
        assert not matcher.load_file(tmp_path / "nonexistent")
    
    def test_filter_paths(self):
        """Test filtering a list of paths."""
        matcher = IgnoreMatcher()
        matcher.add_pattern("*.log")
        matcher.add_pattern("temp/")
        
        paths = ["file.txt", "test.log", "temp/data.txt", "src/main.py"]
        filtered = matcher.filter_paths(paths)
        
        assert "file.txt" in filtered
        assert "src/main.py" in filtered
        assert "test.log" not in filtered


class TestGetIgnoreMatcher:
    """Tests for get_ignore_matcher function."""
    
    def test_always_ignores_lit_dir(self, tmp_path):
        """Should always ignore .lit directory."""
        matcher = get_ignore_matcher(tmp_path)
        assert matcher.is_ignored(".lit")
        assert matcher.is_ignored(".lit/objects/abc")
    
    def test_loads_litignore(self, tmp_path):
        """Should load .litignore if present."""
        (tmp_path / ".litignore").write_text("*.log\n")
        matcher = get_ignore_matcher(tmp_path)
        assert matcher.is_ignored("test.log")
    
    def test_works_without_litignore(self, tmp_path):
        """Should work even without .litignore file."""
        matcher = get_ignore_matcher(tmp_path)
        # Should still ignore .lit
        assert matcher.is_ignored(".lit")
        # Should not ignore regular files
        assert not matcher.is_ignored("test.txt")


class TestCommonPatterns:
    """Test common ignore patterns work correctly."""
    
    def test_python_patterns(self):
        """Test Python-specific patterns."""
        matcher = IgnoreMatcher()
        matcher.add_pattern("__pycache__/")
        matcher.add_pattern("*.py[cod]")
        matcher.add_pattern("*.egg-info/")
        
        assert matcher.is_ignored("__pycache__/module.pyc")
        assert matcher.is_ignored("test.pyc")
        assert matcher.is_ignored("test.pyo")
        assert matcher.is_ignored("mypackage.egg-info/PKG-INFO")
    
    def test_node_patterns(self):
        """Test Node.js-specific patterns."""
        matcher = IgnoreMatcher()
        matcher.add_pattern("node_modules/")
        
        assert matcher.is_ignored("node_modules/express/index.js")
    
    def test_ide_patterns(self):
        """Test IDE-specific patterns."""
        matcher = IgnoreMatcher()
        matcher.add_pattern(".idea/")
        matcher.add_pattern(".vscode/")
        matcher.add_pattern("*.swp")
        
        assert matcher.is_ignored(".idea/workspace.xml")
        assert matcher.is_ignored(".vscode/settings.json")
        assert matcher.is_ignored("file.txt.swp")
    
    def test_os_patterns(self):
        """Test OS-specific patterns."""
        matcher = IgnoreMatcher()
        matcher.add_pattern(".DS_Store")
        matcher.add_pattern("Thumbs.db")
        
        assert matcher.is_ignored(".DS_Store")
        assert matcher.is_ignored("subdir/.DS_Store")
        assert matcher.is_ignored("Thumbs.db")
