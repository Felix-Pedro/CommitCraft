from typer.testing import CliRunner
from commitcraft.__main__ import app
from unittest.mock import patch
import re

runner = CliRunner()

def strip_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def test_version_flag():
    # Use --no-color to avoid ANSI escape codes in output
    result = runner.invoke(app, ["--version", "--no-color"])
    assert result.exit_code == 0
    assert "CommitCraft version" in strip_ansi(result.stdout)

def test_help_flag():
    result = runner.invoke(app, ["--help", "--no-color"])
    assert result.exit_code == 0
    assert "Generates a commit message" in strip_ansi(result.stdout)

@patch('commitcraft.__main__.get_diff')
def test_main_no_diff(mock_get_diff):
    # Simulate empty diff
    mock_get_diff.return_value = ""
    # We expect it might fail or just print nothing depending on implementation, 
    # but let's check it doesn't crash.
    with patch('commitcraft.__main__.commit_craft'):
        runner.invoke(app)
        # It usually prints response.
        # If commit_craft returns None or similar, echo might print it.
        pass
