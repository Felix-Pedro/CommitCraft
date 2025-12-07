import os
import re
import random
import threading

# Force color support by default (fixes zsh detection issues)
# Use --no-color flag or NO_COLOR=1 environment variable to disable
if not os.environ.get('NO_COLOR'):
    os.environ.setdefault('FORCE_COLOR', '1')

from dotenv import load_dotenv
from commitcraft import commit_craft, get_diff, CommitCraftInput, LModelOptions, EmojiConfig, LModel, filter_diff
from .config_handler import interactive_config
import typer
from typing import Optional
from typing_extensions import Annotated
from rich.console import Console
from rich.theme import Theme
from rich.live import Live
from rich.spinner import Spinner

# Define a custom theme that uses standard ANSI colors to respect the user's terminal theme configuration
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "danger": "bold red",
    "success": "bold green",
    "thinking_title": "bold magenta",  # Magenta is often a good accent on both light/dark themes
    "thinking_content": "italic dim"   # Uses default foreground color, dimmed
})

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
        console.print(f"[bold cyan]CommitCraft[/bold cyan] version [green]{version}[/green]")
        raise typer.Exit()

app = typer.Typer(rich_markup_mode="rich")

# Funny loading messages for commit generation
LOADING_MESSAGES = [
    "[success]Asking the AI to read your mind...[/success]",
    "[success]Teaching the model about good commit messages...[/success]",
    "[success]Generating commit message... (No, it's not skynet... yet)[/success]",
    "[success]Consulting the neural oracle...[/success]",
    "[success]Translating diff to human...[/success]",
    "[success]Running git blame on the AI...[/success]",
    "[success]Convincing the LLM this isn't just 'fixed stuff'...[/success]",
    "[success]Teaching robots to write poetry (sort of)...[/success]",
    "[success]Generating commit message... (99 bugs in the code...)[/success]",
    "[success]Asking GPT what you actually changed...[/success]",
    "[success]Warming up the silicon brain cells...[/success]",
    "[success]Turning your diff into Shakespeare...[/success]",
    "[success]Making the commit message sound professional...[/success]",
    "[success]Avoiding 'WIP', 'fix', and 'asdf'...[/success]",
    "[success]Calculating the meaning of your code changes...[/success]",
    "[success]Training AI to understand programmer humor...[/success]",
    "[success]Beep boop... generating human-readable text...[/success]",
    "[success]Channeling the spirit of Linus Torvalds...[/success]",
    "[success]Hoping this commit makes sense...[/success]",
    "[success]Crafting the perfect commit (no pressure)...[/success]",
]

def rotating_status(callable_func, *args, **kwargs):
    """
    Execute a function with a rotating loading message that changes every 3 seconds.
    """
    result = [None]
    exception = [None]
    finished = threading.Event()

    def run_function():
        try:
            result[0] = callable_func(*args, **kwargs)
        except Exception as e:
            exception[0] = e
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
        refresh_per_second=10
    ) as live:
        while not finished.is_set():
            # Wait for 3 seconds or until finished
            if finished.wait(timeout=3.0):
                break

            # Rotate to next message
            message_index = (message_index + 1) % len(messages)
            live.update(Spinner("dots", text=messages[message_index], style="success"))

    # Wait for thread to complete
    thread.join()

    # Re-raise any exception that occurred
    if exception[0]:
        raise exception[0]

    return result[0]

def load_file(filepath):
    """Loads configuration from a TOML, YAML, or JSON file."""
    with open(filepath) as file:
        ext = filepath.split('.')[-1]
        if ext == 'toml':
            import toml
            return toml.load(file)
        elif ext in ['yaml', 'yml']:
            import yaml
            return yaml.safe_load(file)
        elif ext == 'json':
            import json
            return json.load(file)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

def find_default_file(filename, context_dir='./.commitcraft'):
    """Finds the default file in the .commitcraft directory."""
    extensions = ['toml', 'yaml', 'yml', 'json']
    for ext in extensions:
        file_path = os.path.join(context_dir, f'{filename}.{ext}')
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
    config_file = find_default_file('config', directory)
    if config_file:
        return load_file(config_file)

    context_file = find_default_file('context', directory)
    models_file = find_default_file('models', directory)
    emoji_file = find_default_file('emoji', directory)

    if context_file or models_file or emoji_file:
        return {
            "context": load_file(context_file) if context_file else None,
            "models": load_file(models_file) if models_file else None,
            "emoji": load_file(emoji_file) if emoji_file else None
        }
    return {}

def load_config():
    """Load configuration from Global and Project levels and merge them."""
    
    # 1. Global Level
    global_dir = typer.get_app_dir("commitcraft")
    global_config = load_config_from_dir(global_dir)

    # 2. Project Level
    project_dir = './.commitcraft'
    project_config = load_config_from_dir(project_dir)

    # 3. Merge
    return merge_configs(global_config, project_config)

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version", "-v",
            callback=version_callback,
            is_eager=True,
            is_flag=True,
            help="Show version and exit"
        )
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option(
            "--no-color",
            is_flag=True,
            help="Disable colored output (plain text only). Also available as --plain"
        )
    ] = False,
    plain: Annotated[
        bool,
        typer.Option(
            "--plain",
            hidden=True,
            is_flag=True,
            help="Alias for --no-color"
        )
    ] = False,
    config_file: Annotated[
        Optional[str],
        typer.Option(
            help="Path to the config file ([cyan]TOML[/cyan], [cyan]YAML[/cyan], or [cyan]JSON[/cyan])",
            show_default='tries to open [cyan].commitcraft[/cyan] folder in the root of the repo'
        )
    ] = None,
    ignore: Annotated[
        Optional[str],
        typer.Option(
            help="Files or file patterns to [red]ignore[/red] (comma separated)",
            show_default='tries to open [cyan].commitcraft/.ignore[/cyan] file of the repo'
        )
    ] = None,
    debug_prompt: Annotated[
        bool,
        typer.Option(is_flag=True, help="Return the [yellow]prompt[/yellow], don't send any request to the model")
    ] = False,

    provider:  Annotated[
        Optional[str],
        typer.Option(
            rich_help_panel='Model Config',
            envvar="COMMITCRAFT_PROVIDER",
            help="Provider for the AI model (supported: [magenta]ollama[/magenta], [magenta]ollama_cloud[/magenta], [magenta]groq[/magenta], [magenta]google[/magenta], [magenta]openai[/magenta], [magenta]openai_compatible[/magenta])",
            show_default="ollama"
        )
    ] = None,
    model: Annotated[
        Optional[str],
        typer.Option(
            rich_help_panel='Model Config',
            envvar="COMMITCRAFT_MODEL",
            help="Model name (e.g., [cyan]gemma2[/cyan], [cyan]llama3.1:70b[/cyan])",
            show_default="ollama: [cyan]qwen3[/cyan], ollama_cloud: [cyan]qwen3-coder:480b-cloud[/cyan], groq: [cyan]qwen/qwen3-32b[/cyan], google: [cyan]gemini-2.5-pro[/cyan], openai: [cyan]gpt-3.5-turbo[/cyan]"
        )
    ] = None,
    system_prompt: Annotated[Optional[str], typer.Option(rich_help_panel='Model Config', envvar="COMMITCRAFT_SYSTEM_PROMPT", help="System prompt to guide the model")] = None,
    num_ctx: Annotated[Optional[int], typer.Option(rich_help_panel='Model Config', envvar="COMMITCRAFT_NUM_CTX", help="Context size for the model")] = None,
    temperature: Annotated[Optional[float], typer.Option(rich_help_panel='Model Config', envvar="COMMITCRAFT_TEMPERATURE", help="Temperature for the model")] = None,
    max_tokens: Annotated[Optional[int], typer.Option(rich_help_panel='Model Config', envvar="COMMITCRAFT_MAX_TOKENS", help="Maximum number of tokens for the model")] = None,
    host: Annotated[
        Optional[str],
        typer.Option(
            rich_help_panel='Model Config',
            envvar="COMMITCRAFT_HOST",
            help="HTTP or HTTPS host for the provider, required for custom provider, not used for groq"
        )
    ] = None,
    show_thinking: Annotated[
        bool,
        typer.Option(
            rich_help_panel='Model Config',
            envvar="COMMITCRAFT_SHOW_THINKING",
            is_flag=True,
            help="Show the model's thinking process if available"
        )
    ] = False,

    bug: Annotated[
        bool,
        typer.Option(
            rich_help_panel='Commit Clues',
            is_flag=True,
            help="Indicates to the model that the commit [red]fixes a bug[/red], not necessary if using [cyan]--bug-desc[/cyan]"
        )
    ] = False,
    bug_desc: Annotated[
        Optional[str],
        typer.Option(
            rich_help_panel='Commit Clues',
            help="[red]Describes the bug fixed[/red]"
        )
    ] = None,
    feat: Annotated[
        bool,
        typer.Option(
            rich_help_panel='Commit Clues',
            is_flag=True,
            help="Indicates to the model that the commit [green]adds a feature[/green], not necessary if using [cyan]--feat-desc[/cyan]"
        )
    ] = False,
    feat_desc: Annotated[
        Optional[str],
        typer.Option(
            rich_help_panel='Commit Clues',
            help="[green]Describes the feature added[/green]"
        )
    ] = None,
    docs: Annotated[
        bool,
        typer.Option(
            rich_help_panel='Commit Clues',
            is_flag=True,
            help="Indicates to the model that the commit focuses on [blue]documentation[/blue], not necessary if using [cyan]--docs-desc[/cyan]"
        )
    ] = False,
    docs_desc: Annotated[
        Optional[str],
        typer.Option(
            rich_help_panel='Commit Clues',
            help="[blue]Describes the documentation change/addition[/blue]"
        )
    ] = None,
    refact: Annotated[
        bool,
        typer.Option(
            rich_help_panel='Commit Clues',
            is_flag=True,
            help="Indicates to the model that the commit focuses on [yellow]refactoring[/yellow], not necessary if using [cyan]--refact-desc[/cyan]"
        )
    ] = False,
    refact_desc: Annotated[
        Optional[str],
        typer.Option(
            rich_help_panel='Commit Clues',
            help="[yellow]Describes refactoring[/yellow]"
        )
    ] = None,
    context_clue: Annotated[
        Optional[str],
        typer.Option(
            rich_help_panel='Commit Clues', 
            help="Gives the model a custom clue of the current commit"
        )
    ] = None,

     project_name: Annotated[Optional[str], typer.Option(rich_help_panel='Default Context', help="Your Project name")] = None,
     project_language: Annotated[Optional[str], typer.Option(rich_help_panel='Default Context', help="Your Project language")] = None,
     project_description: Annotated[Optional[str], typer.Option(rich_help_panel='Default Context', help="Your Project description")] = None,
     commit_guide: Annotated[Optional[str], typer.Option(rich_help_panel='Default Context', help="Your Project Commit Guidelines")] = None

):
    """
    [bold green]Generates a commit message[/bold green] based on the result of [cyan]git diff --staged -M[/cyan] and your clues, via the LLM you choose.

    [bold yellow]API keys[/bold yellow] can be provided via environment variables or a [cyan].env[/cyan] file.

    Supported environment variable names are:
    • [cyan]OPENAI_API_KEY[/cyan]
    • [cyan]GROQ_API_KEY[/cyan]
    • [cyan]GOOGLE_API_KEY[/cyan]
    • [cyan]CUSTOM_API_KEY[/cyan] (for [magenta]openai_compatible[/magenta] provider)
    • [cyan]OLLAMA_HOST[/cyan] (for [magenta]ollama[/magenta] provider, e.g., [dim]http://localhost:11434[/dim]; this can also be set directly in the configuration file).
    """
    if ctx.invoked_subcommand is None:
        # Handle color output
        if no_color or plain:
            os.environ['NO_COLOR'] = '1'
            os.environ.pop('FORCE_COLOR', None)

        # Load .env first
        load_dotenv(os.path.join(os.getcwd(), ".env"))
        # Load CommitCraft.env if it exists (overrides .env)
        load_dotenv(os.path.join(os.getcwd(), "CommitCraft.env"))

        # Get the git diff
        diff = get_diff()
        if os.path.exists('./.commitcraft/.ignore'):
            with open('./.commitcraft/.ignore') as ignore_file:
                ignored_patterns = list(set([pattern.strip() for pattern in ignore_file.readlines()]))
            if ignore:
                ignored_patterns = list(set([pattern.strip() for pattern in ignore.split(',')] + ignored_patterns))
            diff = filter_diff(diff, ignored_patterns)

        elif ignore:
            diff = filter_diff(diff, [pattern.strip() for pattern in ignore.split(',')])

        # Determine if the context file is provided or try to load the default
        #print(str(config_file))
        config = load_file(config_file) if config_file else load_config()

        context_info = config.get('context') if config.get('context', False) else {'project_name' : project_name, 'project_language' : project_language, 'project_description' : project_description, 'commit_guidelines' : commit_guide}

        emoji_config = EmojiConfig(**config.get('emoji')) if config.get('emoji') else EmojiConfig(emoji_steps='single', emoji_convention='simple')
        
        # Determine model config
        providers_map = config.get('providers', {})
        
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
                base_model_config['api_key'] = resolved_api_key
            
            # Initialize LModel using the named config
            # We must be careful not to override 'provider' with the nickname in the next step
            model_config = LModel(**base_model_config)
            
            # CLI override logic needs adjustment:
            # If user provided --provider <nickname>, we effectively used it to pick the config.
            # We should NOT use 'provider' variable to overwrite model_config.provider unless it was a standard provider.
            # But 'provider' variable holds the nickname string now.
            # So when updating LModel below, we should use model_config.provider instead of 'provider' variable
            # IF we found a match in providers_map.
            cli_provider_override = None # Do not override provider with nickname
            
        else:
            # Fallback to default [models] block or use standard provider defaults
            base_model_config = config.get('models') if config.get('models') else {}
            model_config = LModel(**base_model_config)
            cli_provider_override = provider # Apply CLI override (e.g. 'ollama', 'openai')

        # Construct the model options
        lmodel_options = LModelOptions(
            num_ctx=num_ctx if num_ctx else None,
            temperature=temperature if temperature else None,
            max_tokens=max_tokens if max_tokens else None,
            #**extra_model_options  # Merge extra model options here
        )

        cli_options = lmodel_options.dict()
        config_options = model_config.options.dict() if model_config.options else {}
        model_options = {config: cli_options.get(config) if cli_options.get(config, False) else config_options.get(config) for config in set(list(cli_options.keys()) + list(config_options.keys()))}

        model_config = LModel(
            provider=cli_provider_override if cli_provider_override else model_config.provider,
            model=model if model else model_config.model, # Allow overriding model even for named profile
            system_prompt=system_prompt if system_prompt else model_config.system_prompt,
            host=host if host else model_config.host,
            api_key=model_config.api_key, # Preserve resolved key
            options=LModelOptions(**model_options)
        )

        # Construct the request using provided arguments or defaults
        input = CommitCraftInput(
            diff=diff,
            bug=bug_desc if bug_desc else bug,
            feat=feat_desc if feat_desc else feat,
            docs=docs_desc if docs_desc else docs,
            refact=refact_desc if refact_desc else refact,
            custom_clue=context_clue if context_clue else False

        )

        # Call the commit_craft function with rotating loading messages
        response = rotating_status(
            commit_craft,
            input, model_config, context_info, emoji_config, debug_prompt
        )
        
        # Process <think> tags
        think_pattern = r"<think>(.*?)</think>"
        think_match = re.search(think_pattern, response, re.DOTALL)
        
        if think_match:
            thinking_content = think_match.group(1).strip()
            # Remove the thinking part from the response
            response = re.sub(think_pattern, "", response, flags=re.DOTALL).strip()
            
            if show_thinking:
                err_console.print("[thinking_title]Thinking Process:[/thinking_title]")
                err_console.print(f"[thinking_content]{thinking_content}[/thinking_content]\n")

        typer.echo(response)

@app.command('init')
def init():
    """
    [dim]This Command is not implemented yet.[/dim]
    """
    raise NotImplementedError("This command is not implemented yet")

@app.command('config')
def config():
    """
    [bold cyan]Interactively creates a configuration file.[/bold cyan]

    Launch an interactive wizard to configure CommitCraft settings including:
    • [green]Provider settings[/green] (Ollama, OpenAI, Google, Groq)
    • [yellow]Model selection[/yellow]
    • [magenta]Emoji conventions[/magenta]
    • [blue]Project context[/blue]
    """
    interactive_config()

@app.command('hook')
def hook(
    uninstall: Annotated[
        bool,
        typer.Option("--uninstall", "-u", is_flag=True, help="Remove the CommitCraft git hook")
    ] = False,
    global_hook: Annotated[
        bool,
        typer.Option("--global", "-g", is_flag=True, help="Install as global git hook template")
    ] = False,
    no_interactive: Annotated[
        bool,
        typer.Option("--no-interactive", is_flag=True, help="Disable interactive prompts for CommitClues in the hook")
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
        _install_hook(global_hook, interactive=not no_interactive)

def _install_hook(global_hook: bool, interactive: bool = True):
    """Install the CommitCraft git hook."""
    from pathlib import Path
    import subprocess

    if global_hook:
        # Get git template directory
        try:
            result = subprocess.run(
                ["git", "config", "--global", "init.templatedir"],
                capture_output=True, text=True
            )
            template_dir = result.stdout.strip()

            if not template_dir:
                # Set default template directory
                template_dir = str(Path.home() / ".git-templates")
                subprocess.run(
                    ["git", "config", "--global", "init.templatedir", template_dir],
                    check=True
                )
                console.print(f"[cyan]Set git template directory to:[/cyan] {template_dir}")

            hook_dir = Path(template_dir) / "hooks"
        except subprocess.CalledProcessError as e:
            console.print(f"[danger]Error setting up global hook:[/danger] {e}", style="red")
            raise typer.Exit(1)
    else:
        # Check if we're in a git repository
        try:
            subprocess.run(["git", "rev-parse", "--git-dir"],
                         capture_output=True, check=True)
        except subprocess.CalledProcessError:
            console.print("[danger]Error:[/danger] Not a git repository", style="red")
            console.print("Run [cyan]git init[/cyan] first or use [cyan]--global[/cyan] for global hook")
            raise typer.Exit(1)

        hook_dir = Path(".git/hooks")

    # Create hooks directory if it doesn't exist
    hook_dir.mkdir(parents=True, exist_ok=True)

    hook_path = hook_dir / "prepare-commit-msg"

    # Check if hook already exists and is not ours
    if hook_path.exists():
        with open(hook_path, 'r') as f:
            content = f.read()
            if "CommitCraft" not in content:
                if not typer.confirm(
                    "A prepare-commit-msg hook already exists. Overwrite?",
                    default=False
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

    # Build the update command based on mode and location
    update_flags = ""
    if is_global_install:
        update_flags += " --global"
    if not interactive:
        update_flags += " --no-interactive"

    update_command = f"CommitCraft hook{update_flags}"

    # Create the hook script based on interactive mode
    if interactive:
        hook_script = f'''#!/bin/sh
# CommitCraft Git Hook (Interactive Mode)
# Automatically generates commit messages using AI with optional CommitClues
# Hook Version: {package_version}
# Hook Location: {hook_location}
# Hook Mode: {hook_mode}

COMMIT_MSG_FILE=$1
COMMIT_SOURCE=$2

# Check hook version
HOOK_VERSION="{package_version}"
INSTALLED_VERSION=$(CommitCraft --version 2>/dev/null | sed 's/\\x1b\\[[0-9;]*m//g' | grep -oE "[0-9]+\\.[0-9]+\\.[0-9]+" || echo "unknown")

if [ "$HOOK_VERSION" != "$INSTALLED_VERSION" ] && [ "$INSTALLED_VERSION" != "unknown" ]; then
    printf "\\033[1;33m⚠️  CommitCraft hook is outdated\\033[0m \\033[2m(hook: \\033[1;31m%s\\033[0m\\033[2m, installed: \\033[1;32m%s\\033[0m\\033[2m)\\033[0m\\n" "$HOOK_VERSION" "$INSTALLED_VERSION" >&2
    printf "   \\033[1;36mUpdate with:\\033[0m \\033[1;97m{update_command}\\033[0m\\n" >&2
    echo "" >&2
fi

# Skip if rebase is in progress
if [ -d ".git/rebase-merge" ] || [ -d ".git/rebase-apply" ]; then
    exit 0
fi

# Only generate message for regular commits (not merge, squash, etc.)
if [ -z "$COMMIT_SOURCE" ] || [ "$COMMIT_SOURCE" = "message" ]; then
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
    printf "Your choice (b/f/d/r/n) [n]: "
    read -r COMMIT_TYPE

    # Build CommitCraft arguments based on user input
    COMMITCRAFT_ARGS=""

    case "$COMMIT_TYPE" in
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

    # Generate commit message with CommitCraft
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
        hook_script = f'''#!/bin/sh
# CommitCraft Git Hook (Non-Interactive Mode)
# Automatically generates commit messages using AI
# Hook Version: {package_version}
# Hook Location: {hook_location}
# Hook Mode: {hook_mode}

COMMIT_MSG_FILE=$1
COMMIT_SOURCE=$2

# Check hook version
HOOK_VERSION="{package_version}"
INSTALLED_VERSION=$(CommitCraft --version 2>/dev/null | sed 's/\\x1b\\[[0-9;]*m//g' | grep -oE "[0-9]+\\.[0-9]+\\.[0-9]+" || echo "unknown")

if [ "$HOOK_VERSION" != "$INSTALLED_VERSION" ] && [ "$INSTALLED_VERSION" != "unknown" ]; then
    printf "\\033[1;33m⚠️  CommitCraft hook is outdated\\033[0m \\033[2m(hook: \\033[1;31m%s\\033[0m\\033[2m, installed: \\033[1;32m%s\\033[0m\\033[2m)\\033[0m\\n" "$HOOK_VERSION" "$INSTALLED_VERSION" >&2
    printf "   \\033[1;36mUpdate with:\\033[0m \\033[1;97m{update_command}\\033[0m\\n" >&2
    echo "" >&2
fi

# Skip if rebase is in progress
if [ -d ".git/rebase-merge" ] || [ -d ".git/rebase-apply" ]; then
    exit 0
fi

# Only generate message for regular commits (not merge, squash, etc.)
if [ -z "$COMMIT_SOURCE" ] || [ "$COMMIT_SOURCE" = "message" ]; then
    # Check if there are staged changes
    if git diff --cached --quiet; then
        exit 0
    fi

    # Generate commit message with CommitCraft
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
    with open(hook_path, 'w') as f:
        f.write(hook_script)

    # Make it executable
    hook_path.chmod(0o755)

    mode_text = "[cyan]interactive[/cyan]" if interactive else "[dim]non-interactive[/dim]"

    if global_hook:
        console.print(f"[success]✓[/success] Global git hook installed successfully ({mode_text} mode)!", style="bold green")
        console.print(f"[cyan]Location:[/cyan] {hook_path}")
        console.print("\n[yellow]Note:[/yellow] This will apply to newly initialized repositories.")
        console.print("For existing repos, run [cyan]CommitCraft hook[/cyan] in each repository.")
    else:
        console.print(f"[success]✓[/success] Git hook installed successfully ({mode_text} mode)!", style="bold green")
        console.print(f"[cyan]Location:[/cyan] {hook_path}")
        if interactive:
            console.print("\n[green]Next time you commit, you'll be prompted for commit type and CommitCraft will generate a message![/green]")
        else:
            console.print("\n[green]Next time you commit, CommitCraft will generate a message for you![/green]")

def _uninstall_hook(global_hook: bool):
    """Uninstall the CommitCraft git hook."""
    from pathlib import Path
    import subprocess

    if global_hook:
        try:
            result = subprocess.run(
                ["git", "config", "--global", "init.templatedir"],
                capture_output=True, text=True
            )
            template_dir = result.stdout.strip()

            if not template_dir:
                console.print("[yellow]No global git template directory configured.[/yellow]")
                raise typer.Exit(0)

            hook_path = Path(template_dir) / "hooks" / "prepare-commit-msg"
        except subprocess.CalledProcessError:
            console.print("[danger]Error reading git configuration.[/danger]", style="red")
            raise typer.Exit(1)
    else:
        hook_path = Path(".git/hooks/prepare-commit-msg")

    if not hook_path.exists():
        console.print("[yellow]No CommitCraft hook found.[/yellow]")
        raise typer.Exit(0)

    # Check if it's a CommitCraft hook
    with open(hook_path, 'r') as f:
        content = f.read()
        if "CommitCraft" not in content:
            console.print("[yellow]The existing hook is not a CommitCraft hook.[/yellow]")
            if not typer.confirm("Remove it anyway?", default=False):
                raise typer.Exit(0)

    # Remove the hook
    hook_path.unlink()

    scope = "global" if global_hook else "local"
    console.print(f"[success]✓[/success] CommitCraft {scope} hook removed successfully!", style="bold green")

if __name__ == "__main__":
    app()
