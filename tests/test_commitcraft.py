"""Tests for CommitCraft core git operations."""

import pytest
import subprocess
from unittest.mock import MagicMock, patch

from commitcraft.CommitCraft import get_diff, filter_diff, matches_pattern


class TestGetDiff:
    """Tests for git diff retrieval with error handling."""

    @patch("subprocess.run")
    def test_get_diff_success(self, mock_subprocess_run):
        """Test successful git diff retrieval."""
        mock_subprocess_run.return_value = MagicMock(
            stdout="diff --git a/file1.txt b/file1.txt\n--- a/file1.txt\n+++ b/file1.txt\n@@ -1 +1 @@\n-old line\n+new line\n",
            returncode=0,
        )

        result = get_diff()
        assert "diff --git a/file1.txt b/file1.txt" in result
        mock_subprocess_run.assert_called_once_with(
            ["git", "diff", "--staged", "-M"],
            capture_output=True,
            text=True,
            check=True,
        )

    @patch("subprocess.run")
    def test_get_diff_git_not_installed(self, mock_subprocess_run):
        """Test error handling when git is not installed."""
        mock_subprocess_run.side_effect = FileNotFoundError("git not found")

        with pytest.raises(RuntimeError, match="Git is not installed"):
            get_diff()

    @patch("subprocess.run")
    def test_get_diff_git_error(self, mock_subprocess_run):
        """Test error handling when git command fails."""
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            returncode=128, cmd=["git", "diff"], stderr="fatal: not a git repository"
        )

        with pytest.raises(RuntimeError, match="Git command failed"):
            get_diff()

    @patch("subprocess.run")
    def test_get_diff_amend_success(self, mock_subprocess_run):
        """Test successful git diff retrieval with --amend."""
        # Setup mock responses for:
        # 1. git rev-parse --verify HEAD (True)
        # 2. git rev-parse --verify HEAD^ (True)
        # 3. git diff --cached HEAD^ -M
        mock_subprocess_run.side_effect = [
            MagicMock(returncode=0), # HEAD check
            MagicMock(returncode=0), # HEAD^ check
            MagicMock(stdout="amend diff content", returncode=0) # diff call
        ]

        result = get_diff(amend=True)
        assert result == "amend diff content"
        
        # Verify the calls
        assert mock_subprocess_run.call_count == 3
        mock_subprocess_run.assert_any_call(["git", "rev-parse", "--verify", "HEAD"], check=True, capture_output=True)
        mock_subprocess_run.assert_any_call(["git", "rev-parse", "--verify", "HEAD^"], check=True, capture_output=True)
        mock_subprocess_run.assert_any_call(["git", "diff", "--cached", "HEAD^", "-M"], capture_output=True, text=True, check=True)

    @patch("subprocess.run")
    def test_get_diff_amend_root_commit(self, mock_subprocess_run):
        """Test successful git diff retrieval with --amend for root commit."""
        # Setup mock responses for:
        # 1. git rev-parse --verify HEAD (True)
        # 2. git rev-parse --verify HEAD^ (False)
        # 3. git diff --cached <empty_tree> -M
        mock_subprocess_run.side_effect = [
            MagicMock(returncode=0), # HEAD check
            subprocess.CalledProcessError(1, ["git", "rev-parse"]), # HEAD^ check fails
            MagicMock(stdout="root amend diff content", returncode=0) # diff call
        ]

        result = get_diff(amend=True)
        assert result == "root amend diff content"
        
        # Verify the calls
        assert mock_subprocess_run.call_count == 3
        empty_tree = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
        mock_subprocess_run.assert_any_call(["git", "diff", "--cached", empty_tree, "-M"], capture_output=True, text=True, check=True)


class TestDiffFiltering:
    """Tests for diff filtering and pattern matching."""

    def test_matches_pattern_simple(self):
        """Test simple pattern matching."""
        assert matches_pattern("file.lock", ["*.lock"])
        assert matches_pattern("package-lock.json", ["package-lock.json"])
        assert not matches_pattern("file.txt", ["*.lock"])

    def test_matches_pattern_multiple(self):
        """Test matching against multiple patterns."""
        patterns = ["*.lock", "*.min.js", "*.map"]
        assert matches_pattern("app.min.js", patterns)
        assert matches_pattern("style.map", patterns)
        assert not matches_pattern("app.js", patterns)

    def test_filter_diff_excludes_matched_files(self):
        """Test that matched files are excluded from diff."""
        diff = """diff --git a/src/app.js b/src/app.js
+console.log('hello');
diff --git a/package-lock.json b/package-lock.json
+{
+  "lockfileVersion": 3
+}
diff --git a/src/utils.js b/src/utils.js
+export function utils() {}
"""
        filtered = filter_diff(diff, ["package-lock.json"])
        assert "app.js" in filtered
        assert "utils.js" in filtered
        assert "package-lock.json" not in filtered
        assert "lockfileVersion" not in filtered

    def test_filter_diff_all_files_filtered(self):
        """Test filtering when all files match ignore patterns."""
        diff = """diff --git a/package-lock.json b/package-lock.json
+{
+  "lockfileVersion": 3
+}
diff --git a/yarn.lock b/yarn.lock
+# yarn lockfile
"""
        filtered = filter_diff(diff, ["*.lock", "package-lock.json"])
        # Should be empty or only whitespace
        assert not filtered.strip()

    def test_filter_diff_glob_patterns(self):
        """Test filtering with glob patterns."""
        diff = """diff --git a/src/app.js b/src/app.js
+code
diff --git a/dist/app.min.js b/dist/app.min.js
+minified
diff --git a/src/test.js b/src/test.js
+test
"""
        filtered = filter_diff(diff, ["*.min.js"])
        assert "src/app.js" in filtered
        assert "src/test.js" in filtered
        assert "app.min.js" not in filtered
