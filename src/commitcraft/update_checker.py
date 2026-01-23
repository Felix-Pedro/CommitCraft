"""
Update checker module for CommitCraft.

Checks PyPI for new versions and notifies users about available updates.
Implements weekly caching to avoid excessive API calls.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
from packaging import version

PACKAGE_NAME = "commitcraft"
PYPI_API_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
CACHE_FILENAME = ".update_check"
DEFAULT_CHECK_INTERVAL_DAYS = 7


def get_cache_file_path() -> Path:
    """Get the path to the update check cache file."""
    import typer

    app_dir = Path(typer.get_app_dir("commitcraft"))
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir / CACHE_FILENAME


def get_current_version() -> str:
    """Get the currently installed version of CommitCraft."""
    try:
        import importlib.metadata

        return importlib.metadata.version(PACKAGE_NAME)
    except Exception:
        return "unknown"


def get_latest_version_from_pypi() -> Optional[str]:
    """
    Fetch the latest version from PyPI.

    Returns None if the request fails or times out.
    Uses a 2-second timeout to avoid blocking.
    """
    try:
        response = requests.get(PYPI_API_URL, timeout=2)
        if response.status_code == 200:
            data = response.json()
            return data["info"]["version"]
    except Exception:
        # Silently fail - don't interrupt user workflow
        pass
    return None


def compare_versions(current: str, latest: str) -> bool:
    """
    Compare two version strings.

    Returns True if latest > current, False otherwise.
    Falls back to string comparison if version parsing fails.
    """
    try:
        return version.parse(latest) > version.parse(current)
    except Exception:
        # Fallback to string comparison
        return latest > current


def load_cache() -> Optional[dict]:
    """Load the update check cache file."""
    cache_file = get_cache_file_path()
    if not cache_file.exists():
        return None

    try:
        with open(cache_file, "r") as f:
            return json.load(f)
    except Exception:
        # Corrupted cache, treat as non-existent
        return None


def save_cache(latest_version: str):
    """Save the current check timestamp and latest version to cache."""
    cache_file = get_cache_file_path()
    cache_data = {
        "last_check": datetime.now().isoformat(),
        "latest_version": latest_version,
    }

    try:
        with open(cache_file, "w") as f:
            json.dump(cache_data, f, indent=2)
    except Exception:
        # Silently fail if we can't write cache
        pass


def should_check_for_updates(config: Optional[dict] = None) -> bool:
    """
    Determine if we should check for updates.

    Checks:
    1. If update checking is enabled in config (opt-out by default)
    2. If enough time has passed since last check (default: 7 days)

    Args:
        config: Configuration dictionary with optional 'updates' section

    Returns:
        True if we should check for updates, False otherwise
    """
    # Check if update checking is disabled in config
    if config:
        updates_config = config.get("updates", {})
        if updates_config.get("check_enabled") is False:
            return False
        check_interval_days = updates_config.get(
            "check_interval_days", DEFAULT_CHECK_INTERVAL_DAYS
        )
    else:
        check_interval_days = DEFAULT_CHECK_INTERVAL_DAYS

    # Load cache to check last check time
    cache = load_cache()
    if cache is None:
        # No cache exists, this is first run
        return True

    try:
        last_check = datetime.fromisoformat(cache["last_check"])
        time_since_check = datetime.now() - last_check
        return time_since_check > timedelta(days=check_interval_days)
    except Exception:
        # Corrupted cache, check again
        return True


def check_for_updates(
    config: Optional[dict] = None, force: bool = False
) -> Optional[dict]:
    """
    Check for updates and return update information if available.

    Args:
        config: Configuration dictionary
        force: If True, bypass cache and check immediately

    Returns:
        Dictionary with update info if update is available, None otherwise.
        Format: {"current": "1.0.0", "latest": "1.1.0"}
    """
    # Check if we should perform the check
    if not force and not should_check_for_updates(config):
        return None

    # Get current and latest versions
    current = get_current_version()
    if current == "unknown":
        return None

    latest = get_latest_version_from_pypi()
    if latest is None:
        return None

    # Save to cache regardless of result
    save_cache(latest)

    # Compare versions
    if compare_versions(current, latest):
        return {
            "current": current,
            "latest": latest,
        }

    return None


def format_update_notification(update_info: dict, no_color: bool = False) -> str:
    """
    Format a user-friendly update notification message.

    Args:
        update_info: Dictionary with 'current' and 'latest' version strings
        no_color: If True, return plain text without Rich markup

    Returns:
        Formatted notification string
    """
    current = update_info["current"]
    latest = update_info["latest"]

    if no_color:
        return f"""
╭────────────────────────────────────────────────────╮
│ 🎉 CommitCraft {latest} is available!{" " * (22 - len(latest))}│
│    Current version: {current}{" " * (31 - len(current))}│
│                                                    │
│    Update with:                                    │
│      uv tool upgrade commitcraft                   │
│      pipx upgrade commitcraft                      │
│                                                    │
│    Disable checks: Add to config file              │
│      [updates]                                     │
│      check_enabled = false                         │
╰────────────────────────────────────────────────────╯
"""
    else:
        return f"""
[dim]╭────────────────────────────────────────────────────╮[/dim]
[dim]│[/dim] [bold green]🎉 CommitCraft {latest} is available![/bold green]{" " * (22 - len(latest))}[dim]│[/dim]
[dim]│[/dim]    [yellow]Current version: {current}[/yellow]{" " * (31 - len(current))}[dim]│[/dim]
[dim]│[/dim]                                                    [dim]│[/dim]
[dim]│[/dim]    [cyan]Update with:[/cyan]                                    [dim]│[/dim]
[dim]│[/dim]      [bold]uv tool upgrade commitcraft[/bold]                   [dim]│[/dim]
[dim]│[/dim]      [bold]pipx upgrade commitcraft[/bold]                      [dim]│[/dim]
[dim]│[/dim]                                                    [dim]│[/dim]
[dim]│[/dim]    [dim]Disable checks: Add to config file[/dim]              [dim]│[/dim]
[dim]│[/dim]      [dim]\\[updates][/dim]                                     [dim]│[/dim]
[dim]│[/dim]      [dim]check_enabled = false[/dim]                         [dim]│[/dim]
[dim]╰────────────────────────────────────────────────────╯[/dim]
"""


def check_and_notify_update(
    config: Optional[dict] = None, no_color: bool = False, force: bool = False
):
    """
    Check for updates and print notification if available.

    This is the main entry point for update checking.
    Prints to stderr to avoid interfering with piped output.

    Args:
        config: Configuration dictionary
        no_color: If True, use plain text output
        force: If True, bypass cache and check immediately
    """
    try:
        update_info = check_for_updates(config, force=force)
        if update_info:
            from rich.console import Console

            # Use stderr to avoid interfering with piped output
            err_console = Console(stderr=True)
            message = format_update_notification(update_info, no_color=no_color)

            if no_color:
                import sys

                print(message, file=sys.stderr)
            else:
                err_console.print(message)
    except Exception:
        # Silently fail - never interrupt user workflow
        pass
