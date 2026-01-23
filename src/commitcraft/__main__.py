import os
import queue
import random
import re
import threading
from typing import Any, Optional

# Force color support by default (fixes zsh detection issues)
# Use --no-color flag or NO_COLOR=1 environment variable to disable
if not os.environ.get("NO_COLOR"):
    os.environ.setdefault("FORCE_COLOR", "1")

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.theme import Theme
from typing_extensions import Annotated

from commitcraft import (
    CommitCraftInput,
    EmojiConfig,
    EmojiSteps,
    LModel,
    LModelOptions,
    commit_craft,
    filter_diff,
    get_diff,
)

from .config_handler import interactive_config
from .messages import LOADING_MESSAGES
from .update_checker import check_and_notify_update

# Default patterns to ignore in diffs (these files add noise without useful context)
DEFAULT_IGNORE_PATTERNS = [
    # Lock files
    "*.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    # Minified/bundled assets
    "*.min.js",
    "*.min.css",
    "*.map",
    # Auto-generated files
    "*.snap",
    "*.pb.go",
    "*.pb.js",
    "*_generated.*",
    "*.d.ts",
    # Vector graphics (often large/generated)
    "*.svg",
]


# Define a custom theme that uses standard ANSI colors to respect the user's terminal theme configuration
custom_theme = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "danger": "bold red",
        "success": "bold green",
        "thinking_title": "bold magenta",  # Magenta is often a good accent on both light/dark themes
        "thinking_content": "italic dim",  # Uses default foreground color, dimmed
    }
)

err_console = Console(stderr=True, theme=custom_theme, force_terminal=True)
console = Console(theme=custom_theme, force_terminal=True)

# Configure Rich for Typer's help output
import rich.console  # noqa: E402

rich.console._console = console


def version_callback(value: bool):
    """Display version and exit."""
    if value:
        try:
            import importlib.metadata

            version = importlib.metadata.version("commitcraft")
        except Exception:
            version = "unknown"
        console.print(
            f"[bold cyan]CommitCraft[/bold cyan] version [green]{version}[/green]"
        )
        raise typer.Exit()


app = typer.Typer(rich_markup_mode="rich")


def rotating_status(callable_func, *args, **kwargs):
    """
    Execute a function with a rotating loading message that changes every 4 seconds.
    Safely handles threading and exceptions.
    """
    # Use a Queue for thread-safe result/exception passing
    result_queue: queue.Queue[Any] = queue.Queue()
    finished = threading.Event()

    def run_function():
        try:
            res = callable_func(*args, **kwargs)
            result_queue.put(("result", res))
        except Exception as e:
            result_queue.put(("exception", e))
        finally:
            finished.set()

    # Start the function in a background thread
    thread = threading.Thread(target=run_function, daemon=True)
    thread.start()

    # Shuffle messages to get a random order
    messages = LOADING_MESSAGES.copy()
    random.shuffle(messages)
    message_index = 0

    # Create a live display with rotating messages
    with Live(
        Spinner("dots", text=messages[message_index], style="success"),
        console=err_console,
        refresh_per_second=10,
    ) as live:
        while not finished.is_set():
            # Wait for 4 seconds or until finished
            if finished.wait(timeout=4.0):
                break

            # Rotate to next message
            message_index = (message_index + 1) % len(messages)
            live.update(Spinner("dots", text=messages[message_index], style="success"))

    # Wait for thread to complete with a small timeout to ensure clean join
    # If the thread is stuck (e.g., network hang), join() might block,
    # but since it's a daemon thread, the program can exit if main thread finishes.
    # However, we are in the main thread waiting for result.
    thread.join(timeout=1.0)

    if not result_queue.empty():
        status, value = result_queue.get()
        if status == "exception":
            raise value
        return value
    else:
        # This should rarely happen if finished is set, unless thread died silently
        raise RuntimeError("Thread finished but returned no result")


def load_file(filepath):
    """Loads configuration from a TOML, YAML, or JSON file."""
    with open(filepath) as file:
        ext = filepath.split(".")[-1]
        if ext == "toml":
            import toml

            return toml.load(file)
        elif ext in ["yaml", "yml"]:
            import yaml

            return yaml.safe_load(file)
        elif ext == "json":
            import json

            return json.load(file)
        else:
            raise ValueError(f"Unsupported file type: {ext}")


def find_default_file(filename, context_dir="./.commitcraft"):
    """Finds the default file in the .commitcraft directory."""
    extensions = ["toml", "yaml", "yml", "json"]
    for ext in extensions:
        file_path = os.path.join(context_dir, f"{filename}.{ext}")
        if os.path.exists(file_path):
            return file_path
    return None


def merge_configs(base: dict, override: dict) -> dict:
    """Merge override config into base config."""
    merged = base.copy()
    for key, value in override.items():
        if value is None:
            continue

        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def load_config_from_dir(directory: str) -> dict:
    """Loads configuration from a directory."""
    config_file = find_default_file("config", directory)
    if config_file:
        return load_file(config_file)

    context_file = find_default_file("context", directory)
    models_file = find_default_file("models", directory)
    emoji_file = find_default_file("emoji", directory)

    if context_file or models_file or emoji_file:
        return {
            "context": load_file(context_file) if context_file else None,
            "models": load_file(models_file) if models_file else None,
            "emoji": load_file(emoji_file) if emoji_file else None,
        }
    return {}


def load_config():
    """Load configuration from Global and Project levels and merge them."""

    # 1. Global Level
    global_dir = typer.get_app_dir("commitcraft")
    global_config = load_config_from_dir(global_dir)

    # 2. Project Level
    project_dir = "./.commitcraft"
    project_config = load_config_from_dir(project_dir)

    # 3. Merge
    return merge_configs(global_config, project_config)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            is_flag=True,
            help="Show version and exit",
        ),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option(
            "--no-color",
            is_flag=True,
            help="Disable colored output (plain text only). Also available as --plain",
        ),
    ] = False,
    plain: Annotated[
        bool,
        typer.Option("--plain", hidden=True, is_flag=True, help="Alias for --no-color"),
    ] = False,
    config_file: Annotated[
        Optional[str],
        typer.Option(
            help="Path to the config file ([cyan]TOML[/cyan], [cyan]YAML[/cyan], or [cyan]JSON[/cyan])",
            show_default="tries to open [cyan].commitcraft[/cyan] folder in the root of the repo",
        ),
    ] = None,
    ignore: Annotated[
        Optional[str],
        typer.Option(
            help="Files or file patterns to [red]ignore[/red] (comma separated)",
            show_default="tries to open [cyan].commitcraft/.ignore[/cyan] file of the repo",
        ),
    ] = None,
    debug_prompt: Annotated[
        bool,
        typer.Option(
            is_flag=True,
            help="Return the [yellow]prompt[/yellow], don't send any request to the model",
        ),
    ] = False,
    provider: Annotated[
        Optional[str],
        typer.Option(
            rich_help_panel="Model Config",
            envvar="COMMITCRAFT_PROVIDER",
            help="Provider for the AI model (supported: [magenta]ollama[/magenta], [magenta]ollama_cloud[/magenta], [magenta]groq[/magenta], [magenta]google[/magenta], [magenta]openai[/magenta], [magenta]openai_compatible[/magenta])",
            show_default="ollama",
        ),
    ] = None,
    model: Annotated[
        Optional[str],
        typer.Option(
            rich_help_panel="Model Config",
            envvar="COMMITCRAFT_MODEL",
            help="Model name (e.g., [cyan]gemma2[/cyan], [cyan]llama3.1:70b[/cyan])",
            show_default="ollama: [cyan]qwen3[/cyan], ollama_cloud: [cyan]qwen3-coder:480b-cloud[/cyan], groq: [cyan]qwen/qwen3-32b[/cyan], google: [cyan]gemini-2.5-flash[/cyan], openai: [cyan]gpt-3.5-turbo[/cyan]",
        ),
    ] = None,
    system_prompt: Annotated[
        Optional[str],
        typer.Option(
            rich_help_panel="Model Config",
            envvar="COMMITCRAFT_SYSTEM_PROMPT",
            help="System prompt to guide the model",
        ),
    ] = None,
    num_ctx: Annotated[
        Optional[int],
        typer.Option(
            rich_help_panel="Model Config",
            envvar="COMMITCRAFT_NUM_CTX",
            help="Context size for the model",
        ),
    ] = None,
    min_ctx: Annotated[
        Optional[int],
        typer.Option(
            rich_help_panel="Model Config",
            envvar="COMMITCRAFT_MIN_CONTEXT_SIZE",
            help="Minimum context size (for auto-calculation)",
        ),
    ] = None,
    max_ctx: Annotated[
        Optional[int],
        typer.Option(
            rich_help_panel="Model Config",
            envvar="COMMITCRAFT_MAX_CONTEXT_SIZE",
            help="Maximum context size (for auto-calculation)",
        ),
    ] = None,
    temperature: Annotated[
        Optional[float],
        typer.Option(
            rich_help_panel="Model Config",
            envvar="COMMITCRAFT_TEMPERATURE",
            help="Temperature for the model",
        ),
    ] = None,
    top_p: Annotated[
        Optional[float],
        typer.Option(
            rich_help_panel="Model Config",
            envvar="COMMITCRAFT_TOP_P",
            help="Top-p sampling for the model",
        ),
    ] = None,
    max_tokens: Annotated[
        Optional[int],
        typer.Option(
            rich_help_panel="Model Config",
            envvar="COMMITCRAFT_MAX_TOKENS",
            help="Maximum number of tokens for the model",
        ),
    ] = None,
    host: Annotated[
        Optional[str],
        typer.Option(
            rich_help_panel="Model Config",
            envvar="COMMITCRAFT_HOST",
            help="HTTP or HTTPS host for the provider, required for custom provider, not used for groq",
        ),
    ] = None,
    show_thinking: Annotated[
        bool,
        typer.Option(
            rich_help_panel="Model Config",
            envvar="COMMITCRAFT_SHOW_THINKING",
            is_flag=True,
            help="Show the model's thinking process if available",
        ),
    ] = False,
    bug: Annotated[
        bool,
        typer.Option(
            rich_help_panel="Commit Clues",
            is_flag=True,
            help="Indicates to the model that the commit [red]fixes a bug[/red], not necessary if using [cyan]--bug-desc[/cyan]",
        ),
    ] = False,
    bug_desc: Annotated[
        Optional[str],
        typer.Option(
            rich_help_panel="Commit Clues", help="[red]Describes the bug fixed[/red]"
        ),
    ] = None,
    feat: Annotated[
        bool,
        typer.Option(
            rich_help_panel="Commit Clues",
            is_flag=True,
            help="Indicates to the model that the commit [green]adds a feature[/green], not necessary if using [cyan]--feat-desc[/cyan]",
        ),
    ] = False,
    feat_desc: Annotated[
        Optional[str],
        typer.Option(
            rich_help_panel="Commit Clues",
            help="[green]Describes the feature added[/green]",
        ),
    ] = None,
    docs: Annotated[
        bool,
        typer.Option(
            rich_help_panel="Commit Clues",
            is_flag=True,
            help="Indicates to the model that the commit focuses on [blue]documentation[/blue], not necessary if using [cyan]--docs-desc[/cyan]",
        ),
    ] = False,
    docs_desc: Annotated[
        Optional[str],
        typer.Option(
            rich_help_panel="Commit Clues",
            help="[blue]Describes the documentation change/addition[/blue]",
        ),
    ] = None,
    refact: Annotated[
        bool,
        typer.Option(
            rich_help_panel="Commit Clues",
            is_flag=True,
            help="Indicates to the model that the commit focuses on [yellow]refactoring[/yellow], not necessary if using [cyan]--refact-desc[/cyan]",
        ),
    ] = False,
    refact_desc: Annotated[
        Optional[str],
        typer.Option(
            rich_help_panel="Commit Clues",
            help="[yellow]Describes refactoring[/yellow]",
        ),
    ] = None,
    amend: Annotated[
        bool,
        typer.Option(
            rich_help_panel="Commit Clues",
            is_flag=True,
            help="Generate message for [yellow]git commit --amend[/yellow]",
        ),
    ] = False,
    context_clue: Annotated[
        Optional[str],
        typer.Option(
            rich_help_panel="Commit Clues",
            help="Gives the model a custom clue of the current commit",
        ),
    ] = None,
    project_name: Annotated[
        Optional[str],
        typer.Option(rich_help_panel="Default Context", help="Your Project name"),
    ] = None,
    project_language: Annotated[
        Optional[str],
        typer.Option(rich_help_panel="Default Context", help="Your Project language"),
    ] = None,
    project_description: Annotated[
        Optional[str],
        typer.Option(
            rich_help_panel="Default Context", help="Your Project description"
        ),
    ] = None,
    commit_guide: Annotated[
        Optional[str],
        typer.Option(
            rich_help_panel="Default Context", help="Your Project Commit Guidelines"
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            rich_help_panel="Model Config",
            is_flag=True,
            help="Calculate token usage without generating a message",
        ),
    ] = False,
    confirm: Annotated[
        bool,
        typer.Option(
            envvar="COMMITCRAFT_CONFIRM",
            is_flag=True,
            help="Enable two-step confirmation: show dry-run info and settings, then ask for confirmation before generating",
        ),
    ] = False,
    no_emoji: Annotated[
        bool,
        typer.Option(
            rich_help_panel="Model Config",
            envvar="COMMITCRAFT_NO_EMOJI",
            is_flag=True,
            help="Disable emoji in commit messages (overrides config emoji settings)",
        ),
    ] = False,
):
    """
    [bold green]Generates a commit message[/bold green] based on the result of [cyan]git diff --staged -M[/cyan] and your clues, via the LLM you choose.

    [bold yellow]API keys[/bold yellow] can be provided via environment variables or a [cyan].env[/cyan] file.

    Supported environment variable names are:
    • [cyan]OPENAI_API_KEY[/cyan]
    • [cyan]GROQ_API_KEY[/cyan]
    • [cyan]GOOGLE_API_KEY[/cyan]
    • [cyan]OLLAMA_API_KEY[/cyan] (for [magenta]ollama_cloud[/magenta] or remote instances)
    • [cyan]CUSTOM_API_KEY[/cyan] (for [magenta]openai_compatible[/magenta] provider)
    • [cyan]NICKNAME_API_KEY[/cyan] (for named provider profiles, e.g., [dim]REMOTE_API_KEY[/dim])
    • [cyan]OLLAMA_HOST[/cyan] (for [magenta]ollama[/magenta] provider, e.g., [dim]http://localhost:11434[/dim])
    • [cyan]COMMITCRAFT_MIN_CONTEXT_SIZE[/cyan] / [cyan]COMMITCRAFT_MAX_CONTEXT_SIZE[/cyan] (for context limits)
    """
    if ctx.invoked_subcommand is None:
        # Handle color output
        if no_color or plain:
            os.environ["NO_COLOR"] = "1"
            os.environ.pop("FORCE_COLOR", None)

        # Load .env first
        load_dotenv(os.path.join(os.getcwd(), ".env"))
        # Load CommitCraft.env if it exists (overrides .env)
        load_dotenv(os.path.join(os.getcwd(), "CommitCraft.env"))

        # Get the git diff
        diff = get_diff(amend=amend)

        # Build ignore patterns: defaults + .commitcraft/.ignore + CLI --ignore
        ignored_patterns = list(DEFAULT_IGNORE_PATTERNS)
        if os.path.exists("./.commitcraft/.ignore"):
            with open("./.commitcraft/.ignore") as ignore_file:
                ignored_patterns.extend(
                    [
                        pattern.strip()
                        for pattern in ignore_file.readlines()
                        if pattern.strip()
                    ]
                )
        if ignore:
            ignored_patterns.extend([pattern.strip() for pattern in ignore.split(",")])
        diff = filter_diff(diff, list(set(ignored_patterns)))

        # Validate that there are changes to commit
        if not diff or not diff.strip():
            err_console.print(
                "[yellow]No staged changes to analyze.[/yellow]\n"
                "Either there are no staged changes, or all files are ignored by the filter patterns."
            )
            raise typer.Exit(0)

        # Determine if the context file is provided or try to load the default
        # print(str(config_file))
        config = load_file(config_file) if config_file else load_config()

        context_info = (
            config.get("context")
            if config.get("context", False)
            else {
                "project_name": project_name,
                "project_language": project_language,
                "project_description": project_description,
                "commit_guidelines": commit_guide,
            }
        )

        # Handle emoji configuration - CLI --no-emoji flag overrides config
        if no_emoji:
            emoji_config = EmojiConfig(
                emoji_steps=EmojiSteps.false, emoji_convention="simple"
            )
        else:
            emoji_config = (
                EmojiConfig(**config.get("emoji"))
                if config.get("emoji")
                else EmojiConfig(
                    emoji_steps=EmojiSteps.single, emoji_convention="simple"
                )
            )

        # Determine model config
        providers_map = config.get("providers", {})

        # Check if 'provider' argument matches a named provider configuration
        if provider and provider in providers_map:
            # Load the named provider config
            base_model_config = providers_map[provider]

            # Resolve API Key dynamically based on nickname
            # Format: NICKNAME_API_KEY (e.g., REMOTE_API_KEY)
            nickname = provider
            env_key = f"{nickname.upper()}_API_KEY"

            resolved_api_key = os.getenv(env_key)
            if resolved_api_key:
                base_model_config["api_key"] = resolved_api_key

            # Store the nickname so it can be displayed in dry-run output
            base_model_config["nickname"] = nickname

            # Initialize LModel using the named config
            # We must be careful not to override 'provider' with the nickname in the next step
            model_config = LModel(**base_model_config)

            # CLI override logic needs adjustment:
            # If user provided --provider <nickname>, we effectively used it to pick the config.
            # We should NOT use 'provider' variable to overwrite model_config.provider unless it was a standard provider.
            # But 'provider' variable holds the nickname string now.
            # So when updating LModel below, we should use model_config.provider instead of 'provider' variable
            # IF we found a match in providers_map.
            cli_provider_override = None  # Do not override provider with nickname

        else:
            # Fallback to default [models] block or use standard provider defaults
            base_model_config = config.get("models") if config.get("models") else {}
            model_config = LModel(**base_model_config)
            cli_provider_override = (
                provider  # Apply CLI override (e.g. 'ollama', 'openai')
            )

        # Construct the model options
        lmodel_options = LModelOptions(
            num_ctx=num_ctx if num_ctx else None,
            min_ctx=min_ctx if min_ctx else None,
            max_ctx=max_ctx if max_ctx else None,
            temperature=temperature if temperature else None,
            max_tokens=max_tokens if max_tokens else None,
            top_p=top_p if top_p else None,
            # **extra_model_options  # Merge extra model options here
        )

        cli_options = lmodel_options.model_dump()
        config_options = (
            model_config.options.model_dump() if model_config.options else {}
        )
        model_options = {
            config: cli_options.get(config)
            if cli_options.get(config, False)
            else config_options.get(config)
            for config in set(list(cli_options.keys()) + list(config_options.keys()))
        }

        model_config = LModel(
            provider=cli_provider_override
            if cli_provider_override
            else model_config.provider,
            model=model
            if model
            else model_config.model,  # Allow overriding model even for named profile
            system_prompt=system_prompt
            if system_prompt
            else model_config.system_prompt,
            host=host if host else model_config.host,
            api_key=model_config.api_key,  # Preserve resolved key
            options=LModelOptions(**model_options),
            nickname=model_config.nickname,  # Preserve nickname for named providers
        )

        # Construct the request using provided arguments or defaults
        input = CommitCraftInput(
            diff=diff,
            bug=bug_desc if bug_desc else bug,
            feat=feat_desc if feat_desc else feat,
            docs=docs_desc if docs_desc else docs,
            refact=refact_desc if refact_desc else refact,
            custom_clue=context_clue if context_clue else False,
        )

        if dry_run or confirm:
            response = commit_craft(
                input,
                model_config,
                context_info,
                emoji_config,
                debug_prompt,
                dry_run=True,
            )

            if no_color or plain:
                import json

                print(json.dumps(response, indent=2))
            else:
                from rich.table import Table

                table = Table(
                    title="CommitCraft Dry Run"
                    if dry_run
                    else "CommitCraft Configuration Preview"
                )
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green")

                for key, value in response.items():
                    key_fmt = key.replace("_", " ").title()
                    table.add_row(key_fmt, str(value))

                console.print(table)

            # If only dry_run (not confirm), exit here
            if dry_run and not confirm:
                return

            # If confirm mode, ask for user confirmation
            if confirm:
                if no_color or plain:
                    # Plain text confirmation
                    import sys

                    print(
                        "\nProceed with commit message generation? (y/n): ",
                        end="",
                        file=sys.stderr,
                    )
                    sys.stderr.flush()
                    response_input = input().strip().lower()
                    if response_input not in ("y", "yes"):
                        err_console.print("Cancelled by user.")
                        raise typer.Exit(0)
                else:
                    # Rich confirmation
                    if not typer.confirm(
                        "\nProceed with commit message generation?", default=True
                    ):
                        err_console.print("[yellow]Cancelled by user.[/yellow]")
                        raise typer.Exit(0)

        # Call the commit_craft function with rotating loading messages
        response = rotating_status(
            commit_craft, input, model_config, context_info, emoji_config, debug_prompt
        )

        # Process <think> tags (handling multiple occurrences)
        think_pattern = r"<think>(.*?)</think>"
        thinking_blocks = re.findall(think_pattern, response, re.DOTALL)

        if thinking_blocks:
            # Combine all thinking blocks
            all_thoughts = "\n---\n".join(block.strip() for block in thinking_blocks)

            # Remove all thinking parts from the response
            response = re.sub(think_pattern, "", response, flags=re.DOTALL).strip()

            if show_thinking:
                err_console.print("[thinking_title]Thinking Process:[/thinking_title]")
                err_console.print(
                    f"[thinking_content]{all_thoughts}[/thinking_content]\n"
                )

        typer.echo(response)

        # Check for updates after successful commit message generation
        # Only check if not in dry-run mode and not using --version or --help
        check_and_notify_update(config=config, no_color=(no_color or plain))


@app.command("init")
def init():
    """
    [dim]This Command is not implemented yet.[/dim]
    """
    raise NotImplementedError("This command is not implemented yet")


@app.command("config")
def config(
    generate_ignore: Annotated[
        bool,
        typer.Option(
            "--generate-ignore",
            "-i",
            is_flag=True,
            help="Generate a [cyan].commitcraft/.ignore[/cyan] file with default patterns",
        ),
    ] = False,
):
    """
    [bold cyan]Interactively creates a configuration file.[/bold cyan]

    Launch an interactive wizard to configure CommitCraft settings including:
    • [green]Provider settings[/green] (Ollama, OpenAI, Google, Groq)
    • [yellow]Model selection[/yellow]
    • [magenta]Emoji conventions[/magenta]
    • [blue]Project context[/blue]

    Use [cyan]--generate-ignore[/cyan] to create a .ignore file with default patterns.
    """
    # Load .env files to make API keys available for model listing
    load_dotenv(os.path.join(os.getcwd(), ".env"))
    load_dotenv(os.path.join(os.getcwd(), "CommitCraft.env"))

    if generate_ignore:
        ignore_dir = ".commitcraft"
        ignore_file = os.path.join(ignore_dir, ".ignore")

        # Create directory if it doesn't exist
        os.makedirs(ignore_dir, exist_ok=True)

        # Check if file already exists
        if os.path.exists(ignore_file):
            console.print(f"[yellow]⚠ {ignore_file} already exists.[/yellow]")
            overwrite = typer.confirm("Overwrite?", default=False)
            if not overwrite:
                console.print("[dim]Aborted.[/dim]")
                raise typer.Exit()

        # Write defaults with comments
        content = """# CommitCraft ignore patterns
# Files matching these patterns will be excluded from the diff sent to the LLM
# Uses fnmatch syntax (*, ?, [seq], [!seq])

# Lock files
*.lock
package-lock.json
pnpm-lock.yaml

# Minified/bundled assets
*.min.js
*.min.css
*.map

# Auto-generated files
*.snap
*.pb.go
*.pb.js
*_generated.*
*.d.ts

# Vector graphics (often large/generated)
*.svg

# Add your custom patterns below:
"""
        with open(ignore_file, "w") as f:
            f.write(content)

        console.print(f"[green]✓ Created {ignore_file} with default patterns.[/green]")
        console.print("[dim]Edit the file to customize which files to ignore.[/dim]")
        return

    interactive_config()


@app.command("hook")
def hook(
    uninstall: Annotated[
        bool,
        typer.Option(
            "--uninstall", "-u", is_flag=True, help="Remove the CommitCraft git hook"
        ),
    ] = False,
    global_hook: Annotated[
        bool,
        typer.Option(
            "--global", "-g", is_flag=True, help="Install as global git hook template"
        ),
    ] = False,
    no_interactive: Annotated[
        bool,
        typer.Option(
            "--no-interactive",
            is_flag=True,
            help="Disable interactive prompts for CommitClues in the hook",
        ),
    ] = False,
    confirm: Annotated[
        bool,
        typer.Option(
            "--confirm",
            is_flag=True,
            help="Enable two-step confirmation in the hook: show dry-run info before generating",
        ),
    ] = False,
):
    """
    [bold cyan]Set up CommitCraft as a git commit hook.[/bold cyan]

    Installs a [yellow]prepare-commit-msg[/yellow] hook that automatically generates commit messages.
    The generated message will be pre-filled in your editor for you to review and edit.

    [bold]Modes:[/bold]
    • [cyan]Interactive (default)[/cyan]: Prompts for commit type (bug/feature/docs/refactor) and optional description
    • [dim]Non-interactive[/dim]: Generates messages without prompts (use [yellow]--no-interactive[/yellow])

    [bold]Installation:[/bold]
    • [green]Local install[/green]: Installs hook in current repository's .git/hooks/
    • [blue]Global install[/blue]: Sets up git template for all new repositories
    • [red]Uninstall[/red]: Removes the CommitCraft hook
    """

    if uninstall:
        _uninstall_hook(global_hook)
    else:
        _install_hook(global_hook, interactive=not no_interactive, confirm=confirm)


def _install_hook(global_hook: bool, interactive: bool = True, confirm: bool = False):
    """Install the CommitCraft git hook."""
    import subprocess
    from pathlib import Path

    # Check for updates when installing/updating hooks
    check_and_notify_update()

    if global_hook:
        # Get git template directory
        try:
            result = subprocess.run(
                ["git", "config", "--global", "init.templatedir"],
                capture_output=True,
                text=True,
            )
            template_dir = result.stdout.strip()

            if not template_dir:
                # Set default template directory
                template_dir = str(Path.home() / ".git-templates")
                subprocess.run(
                    ["git", "config", "--global", "init.templatedir", template_dir],
                    check=True,
                )
                console.print(
                    f"[cyan]Set git template directory to:[/cyan] {template_dir}"
                )

            hook_dir = Path(template_dir) / "hooks"
        except subprocess.CalledProcessError as e:
            console.print(
                f"[danger]Error setting up global hook:[/danger] {e}", style="red"
            )
            raise typer.Exit(1)
    else:
        # Check if we're in a git repository
        try:
            subprocess.run(
                ["git", "rev-parse", "--git-dir"], capture_output=True, check=True
            )
        except subprocess.CalledProcessError:
            console.print("[danger]Error:[/danger] Not a git repository", style="red")
            console.print(
                "Run [cyan]git init[/cyan] first or use [cyan]--global[/cyan] for global hook"
            )
            raise typer.Exit(1)

        hook_dir = Path(".git/hooks")

    # Create hooks directory if it doesn't exist
    hook_dir.mkdir(parents=True, exist_ok=True)

    hook_path = hook_dir / "prepare-commit-msg"

    # Check if hook already exists and is not ours
    if hook_path.exists():
        with open(hook_path, "r") as f:
            content = f.read()
            if "CommitCraft" not in content:
                if not typer.confirm(
                    "A prepare-commit-msg hook already exists. Overwrite?",
                    default=False,
                ):
                    console.print("[yellow]Installation cancelled.[/yellow]")
                    raise typer.Exit(0)

    # Get the current version from package
    try:
        import importlib.metadata

        package_version = importlib.metadata.version("commitcraft")
    except Exception:
        package_version = "unknown"

    # Determine if this is a global or local hook based on the hook_dir
    is_global_install = global_hook
    hook_location = "global" if is_global_install else "local"
    hook_mode = "interactive" if interactive else "non-interactive"
    if confirm:
        hook_mode += " + confirm"

    # Build the update command based on mode and location
    update_flags = ""
    if is_global_install:
        update_flags += " --global"
    if not interactive:
        update_flags += " --no-interactive"
    if confirm:
        update_flags += " --confirm"

    update_command = f"CommitCraft hook{update_flags}"

    # Track if confirmation was requested during installation
    hook_has_confirm = "1" if confirm else ""

    # Create the hook script based on interactive mode
    if interactive:
        hook_script = rf'''#!/bin/sh
# CommitCraft Git Hook (Interactive Mode)
# Automatically generates commit messages using AI with optional CommitClues
# Hook Version: {package_version}
# Hook Location: {hook_location}
# Hook Mode: {hook_mode}

COMMIT_MSG_FILE=$1
COMMIT_SOURCE=$2

# Check hook version
HOOK_VERSION="{package_version}"
INSTALLED_VERSION=$(CommitCraft --version 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' | grep -oE "[0-9]+\.[0-9]+\.[0-9]+" || echo "unknown")

if [ "$HOOK_VERSION" != "$INSTALLED_VERSION" ] && [ "$INSTALLED_VERSION" != "unknown" ]; then
    printf "\033[1;33m⚠️  CommitCraft hook is outdated\033[0m \033[2m(hook: \033[1;31m%s\033[0m\033[2m, installed: \033[1;32m%s\033[0m\033[2m)\033[0m\n" "$HOOK_VERSION" "$INSTALLED_VERSION" >&2
    printf "   \033[1;36mUpdate with:\033[0m \033[1;97m{update_command}\033[0m\n" >&2
    echo "" >&2
fi

# Check for CommitCraft updates (weekly, non-blocking)
python3 -c "
try:
    from commitcraft.update_checker import check_and_notify_update
    check_and_notify_update(no_color=False)
except Exception:
    pass
" 2>/dev/null || true

# Skip if COMMITCRAFT_SKIP is set
if [ -n "$COMMITCRAFT_SKIP" ]; then
    exit 0
fi

# Skip if rebase is in progress
if [ -d ".git/rebase-merge" ] || [ -d ".git/rebase-apply" ]; then
    exit 0
fi

# Only generate message for regular commits (not merge, squash, amend, or -m flag)
# Skip if user provided their own message with -m flag
if [ -z "$COMMIT_SOURCE" ]; then
    # Check if there are staged changes
    if git diff --cached --quiet; then
        exit 0
    fi

    # Interactive prompt for commit type
    # Redirect input from terminal to make read work in git hook
    exec < /dev/tty

    echo "CommitCraft: What type of commit is this?"
    echo "  [b] Bug fix"
    echo "  [f] Feature"
    echo "  [d] Documentation"
    echo "  [r] Refactoring"
    echo "  [n] None (no specific type)"
    echo "  [s] Skip (write message manually)"
    printf "Your choice (b/f/d/r/n/s) [n]: "
    read -r COMMIT_TYPE

    # Build CommitCraft arguments based on user input
    COMMITCRAFT_ARGS=""

    case "$COMMIT_TYPE" in
        s|S)
            # User wants to skip and write manually
            exit 0
            ;;
        b|B)
            printf "Describe the bug fix (optional): "
            read -r BUG_DESC
            if [ -n "$BUG_DESC" ]; then
                COMMITCRAFT_ARGS="--bug-desc"
                COMMITCRAFT_DESC="$BUG_DESC"
            else
                COMMITCRAFT_ARGS="--bug"
            fi
            ;;
        f|F)
            printf "Describe the feature (optional): "
            read -r FEAT_DESC
            if [ -n "$FEAT_DESC" ]; then
                COMMITCRAFT_ARGS="--feat-desc"
                COMMITCRAFT_DESC="$FEAT_DESC"
            else
                COMMITCRAFT_ARGS="--feat"
            fi
            ;;
        d|D)
            printf "Describe the documentation change (optional): "
            read -r DOCS_DESC
            if [ -n "$DOCS_DESC" ]; then
                COMMITCRAFT_ARGS="--docs-desc"
                COMMITCRAFT_DESC="$DOCS_DESC"
            else
                COMMITCRAFT_ARGS="--docs"
            fi
            ;;
        r|R)
            printf "Describe the refactoring (optional): "
            read -r REFACT_DESC
            if [ -n "$REFACT_DESC" ]; then
                COMMITCRAFT_ARGS="--refact-desc"
                COMMITCRAFT_DESC="$REFACT_DESC"
            else
                COMMITCRAFT_ARGS="--refact"
            fi
            ;;
        *)
            # No specific type, use default
            ;;
    esac

    # Check if confirmation mode is enabled (via hook --confirm or COMMITCRAFT_CONFIRM env var)
    ENABLE_CONFIRMATION="{hook_has_confirm}"
    if [ -n "$COMMITCRAFT_CONFIRM" ]; then
        ENABLE_CONFIRMATION="1"
    fi

    # If confirmation is enabled, show dry-run first and ask for confirmation
    if [ -n "$ENABLE_CONFIRMATION" ]; then
        # Unset COMMITCRAFT_CONFIRM to prevent CLI from showing its own confirmation
        unset COMMITCRAFT_CONFIRM

        echo "" >&2
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
        echo "  Dry-Run Preview (Confirmation Mode)" >&2
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2

        # Run dry-run to show token usage
        if [ -n "$COMMITCRAFT_DESC" ]; then
            CommitCraft --dry-run $COMMITCRAFT_ARGS "$COMMITCRAFT_DESC" >&2
        elif [ -n "$COMMITCRAFT_ARGS" ]; then
            CommitCraft --dry-run $COMMITCRAFT_ARGS >&2
        else
            CommitCraft --dry-run >&2
        fi

        echo "" >&2
        printf "Proceed with commit message generation? (Y/n): " >&2
        read -r CONFIRM_RESPONSE

        case "$CONFIRM_RESPONSE" in
            [Nn]|[Nn][Oo])
                echo "Cancelled by user." >&2
                exit 1
                ;;
        esac
        echo "" >&2
    fi

    # Generate commit message with CommitCraft (without --confirm flag)

    # Pass description as a separate argument to avoid quoting issues
    if [ -n "$COMMITCRAFT_DESC" ]; then
        GENERATED_MSG=$(CommitCraft $COMMITCRAFT_ARGS "$COMMITCRAFT_DESC")
    elif [ -n "$COMMITCRAFT_ARGS" ]; then
        GENERATED_MSG=$(CommitCraft $COMMITCRAFT_ARGS)
    else
        GENERATED_MSG=$(CommitCraft)
    fi

    if [ $? -eq 0 ] && [ -n "$GENERATED_MSG" ]; then
        # Prepend generated message to commit message file
        echo "$GENERATED_MSG" > "$COMMIT_MSG_FILE.tmp"
        echo "" >> "$COMMIT_MSG_FILE.tmp"
        echo "# AI-generated commit message above. Edit as needed." >> "$COMMIT_MSG_FILE.tmp"
        cat "$COMMIT_MSG_FILE" >> "$COMMIT_MSG_FILE.tmp"
        mv "$COMMIT_MSG_FILE.tmp" "$COMMIT_MSG_FILE"
    fi
fi
'''
    else:
        hook_script = rf'''#!/bin/sh
# CommitCraft Git Hook (Non-Interactive Mode)
# Automatically generates commit messages using AI
# Hook Version: {package_version}
# Hook Location: {hook_location}
# Hook Mode: {hook_mode}

COMMIT_MSG_FILE=$1
COMMIT_SOURCE=$2

# Check hook version
HOOK_VERSION="{package_version}"
INSTALLED_VERSION=$(CommitCraft --version 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' | grep -oE "[0-9]+\.[0-9]+\.[0-9]+" || echo "unknown")

if [ "$HOOK_VERSION" != "$INSTALLED_VERSION" ] && [ "$INSTALLED_VERSION" != "unknown" ]; then
    printf "\033[1;33m⚠️  CommitCraft hook is outdated\033[0m \033[2m(hook: \033[1;31m%s\033[0m\033[2m, installed: \033[1;32m%s\033[0m\033[2m)\033[0m\n" "$HOOK_VERSION" "$INSTALLED_VERSION" >&2
    printf "   \033[1;36mUpdate with:\033[0m \033[1;97m{update_command}\033[0m\n" >&2
    echo "" >&2
fi

# Check for CommitCraft updates (weekly, non-blocking)
python3 -c "
try:
    from commitcraft.update_checker import check_and_notify_update
    check_and_notify_update(no_color=False)
except Exception:
    pass
" 2>/dev/null || true

# Skip if COMMITCRAFT_SKIP is set
if [ -n "$COMMITCRAFT_SKIP" ]; then
    exit 0
fi

# Skip if rebase is in progress
if [ -d ".git/rebase-merge" ] || [ -d ".git/rebase-apply" ]; then
    exit 0
fi

# Only generate message for regular commits (not merge, squash, amend, or -m flag)
# Skip if user provided their own message with -m flag
if [ -z "$COMMIT_SOURCE" ]; then
    # Check if there are staged changes
    if git diff --cached --quiet; then
        exit 0
    fi

    # Check if confirmation mode is enabled (via hook --confirm or COMMITCRAFT_CONFIRM env var)
    ENABLE_CONFIRMATION="{hook_has_confirm}"
    if [ -n "$COMMITCRAFT_CONFIRM" ]; then
        ENABLE_CONFIRMATION="1"
    fi

    # If confirmation is enabled, show dry-run first and ask for confirmation
    if [ -n "$ENABLE_CONFIRMATION" ]; then
        # Redirect input from terminal to make read work in git hook
        exec < /dev/tty

        # Unset COMMITCRAFT_CONFIRM to prevent CLI from showing its own confirmation
        unset COMMITCRAFT_CONFIRM

        echo "" >&2
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2
        echo "  Dry-Run Preview (Confirmation Mode)" >&2
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >&2

        # Run dry-run to show token usage
        CommitCraft --dry-run >&2

        echo "" >&2
        printf "Proceed with commit message generation? (Y/n): " >&2
        read -r CONFIRM_RESPONSE

        case "$CONFIRM_RESPONSE" in
            [Nn]|[Nn][Oo])
                echo "Cancelled by user." >&2
                exit 1
                ;;
        esac
        echo "" >&2
    fi

    # Generate commit message with CommitCraft (without --confirm flag)

    # stderr goes to terminal (shows loading spinner), stdout captured
    GENERATED_MSG=$(CommitCraft)

    if [ $? -eq 0 ] && [ -n "$GENERATED_MSG" ]; then
        # Prepend generated message to commit message file
        echo "$GENERATED_MSG" > "$COMMIT_MSG_FILE.tmp"
        echo "" >> "$COMMIT_MSG_FILE.tmp"
        echo "# AI-generated commit message above. Edit as needed." >> "$COMMIT_MSG_FILE.tmp"
        cat "$COMMIT_MSG_FILE" >> "$COMMIT_MSG_FILE.tmp"
        mv "$COMMIT_MSG_FILE.tmp" "$COMMIT_MSG_FILE"
    fi
fi
'''

    # Write the hook script
    with open(hook_path, "w") as f:
        f.write(hook_script)

    # Make it executable
    hook_path.chmod(0o755)

    mode_text = (
        "[cyan]interactive[/cyan]" if interactive else "[dim]non-interactive[/dim]"
    )
    if confirm:
        mode_text += " [yellow]+ confirm[/yellow]"

    if global_hook:
        console.print(
            f"[success]✓[/success] Global git hook installed successfully ({mode_text} mode)!",
            style="bold green",
        )
        console.print(f"[cyan]Location:[/cyan] {hook_path}")
        console.print(
            "\n[yellow]Note:[/yellow] This will apply to newly initialized repositories."
        )
        console.print(
            "For existing repos, run [cyan]CommitCraft hook[/cyan] in each repository."
        )
    else:
        console.print(
            f"[success]✓[/success] Git hook installed successfully ({mode_text} mode)!",
            style="bold green",
        )
        console.print(f"[cyan]Location:[/cyan] {hook_path}")
        if interactive:
            console.print(
                "\n[green]Next time you commit, you'll be prompted for commit type and CommitCraft will generate a message![/green]"
            )
        else:
            console.print(
                "\n[green]Next time you commit, CommitCraft will generate a message for you![/green]"
            )


@app.command("unhook")
def unhook(
    global_hook: Annotated[
        bool,
        typer.Option(
            "--global", "-g", is_flag=True, help="Remove the global git hook template"
        ),
    ] = False,
):
    """
    [bold red]Remove the CommitCraft git hook.[/bold red]

    This command removes the [yellow]prepare-commit-msg[/yellow] hook installed by CommitCraft.

    [bold]Options:[/bold]
    • [green]Local (default)[/green]: Removes hook from current repository
    • [blue]Global[/blue]: Removes hook from git template directory (use [yellow]--global[/yellow])

    [dim]Alias for: CommitCraft hook --uninstall[/dim]
    """
    _uninstall_hook(global_hook)


def _uninstall_hook(global_hook: bool):
    """Uninstall the CommitCraft git hook."""
    import subprocess
    from pathlib import Path

    if global_hook:
        try:
            result = subprocess.run(
                ["git", "config", "--global", "init.templatedir"],
                capture_output=True,
                text=True,
            )
            template_dir = result.stdout.strip()

            if not template_dir:
                console.print(
                    "[yellow]No global git template directory configured.[/yellow]"
                )
                raise typer.Exit(0)

            hook_path = Path(template_dir) / "hooks" / "prepare-commit-msg"
        except subprocess.CalledProcessError:
            console.print(
                "[danger]Error reading git configuration.[/danger]", style="red"
            )
            raise typer.Exit(1)
    else:
        hook_path = Path(".git/hooks/prepare-commit-msg")

    if not hook_path.exists():
        console.print("[yellow]No CommitCraft hook found.[/yellow]")
        raise typer.Exit(0)

    # Check if it's a CommitCraft hook
    with open(hook_path, "r") as f:
        content = f.read()
        if "CommitCraft" not in content:
            console.print(
                "[yellow]The existing hook is not a CommitCraft hook.[/yellow]"
            )
            if not typer.confirm("Remove it anyway?", default=False):
                raise typer.Exit(0)

    # Remove the hook
    hook_path.unlink()

    scope = "global" if global_hook else "local"
    console.print(
        f"[success]✓[/success] CommitCraft {scope} hook removed successfully!",
        style="bold green",
    )


if __name__ == "__main__":
    app()
