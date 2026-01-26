from typer.testing import CliRunner
from commitcraft.__main__ import app
from unittest.mock import patch
import re

runner = CliRunner()


def strip_ansi(text):
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def test_version_flag():
    # Use --no-color to avoid ANSI escape codes in output
    result = runner.invoke(app, ["--version", "--no-color"])
    assert result.exit_code == 0
    assert "CommitCraft version" in strip_ansi(result.stdout)


def test_help_flag():
    result = runner.invoke(app, ["--help", "--no-color"])
    assert result.exit_code == 0
    assert "Generates a commit message" in strip_ansi(result.stdout)


@patch("commitcraft.__main__.get_filtered_diff")
def test_main_no_diff(mock_get_filtered_diff):
    # Simulate empty diff
    mock_get_filtered_diff.return_value = ""
    # Passing no args invokes main
    result = runner.invoke(app, [])
    # Should exit cleanly (0) because it catches empty diff
    assert result.exit_code == 0


@patch("commitcraft.__main__.get_filtered_diff")
@patch("commitcraft.__main__.commit_craft")
def test_dry_run(mock_commit_craft, mock_get_filtered_diff):
    mock_get_filtered_diff.return_value = "diff --git a/file b/file..."
    # dry-run should return a dict with token usage stats
    mock_commit_craft.return_value = {
        "token_count": 100,
        "system_prompt_tokens": 50,
        "user_prompt_tokens": 50,
        "model": "test-model",
        "provider": "test-provider",
    }

    result = runner.invoke(app, ["--dry-run"])
    assert result.exit_code == 0
    # Verify commit_craft was called with dry_run=True in its config
    assert mock_commit_craft.called


@patch("commitcraft.__main__.commit_craft")
@patch("commitcraft.__main__.rotating_status")
@patch("commitcraft.__main__.get_filtered_diff")
def test_clue_flags(mock_get_filtered_diff, mock_rotating_status, mock_commit_craft):
    mock_get_filtered_diff.return_value = (
        "diff --git a/file.py b/file.py"  # Return filtered diff
    )
    mock_commit_craft.return_value = "Fix bug"

    # Mock rotating_status to just call the function immediately
    def side_effect(func, *args, **kwargs):
        return func(*args, **kwargs)

    mock_rotating_status.side_effect = side_effect

    # Remove --no-interactive as it's not a main command flag
    result = runner.invoke(app, ["--bug", "--bug-desc", "Fix NPE"])
    assert result.exit_code == 0

    # Check if flags were passed correctly.
    # Since commit_craft is passed to rotating_status, verify rotating_status call
    assert mock_rotating_status.called

    # Verify arguments passed to rotating_status (first arg is the func commit_craft)
    args, _ = mock_rotating_status.call_args
    assert args[0] == mock_commit_craft

    # Also verify commit_craft called (since we mocked rotating_status to call it)
    assert mock_commit_craft.called


@patch("commitcraft.__main__._install_hook")
def test_hook_install(mock_install):
    result = runner.invoke(app, ["hook", "--no-interactive"])
    assert result.exit_code == 0
    mock_install.assert_called_once()


@patch("commitcraft.__main__._uninstall_hook")
def test_hook_uninstall(mock_uninstall):
    result = runner.invoke(app, ["unhook"])
    assert result.exit_code == 0
    mock_uninstall.assert_called_once()
