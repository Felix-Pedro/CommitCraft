"""Tests for CommitCraft core git operations."""

import pytest
import subprocess
from unittest.mock import MagicMock, patch

from commitcraft.CommitCraft import get_diff


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
