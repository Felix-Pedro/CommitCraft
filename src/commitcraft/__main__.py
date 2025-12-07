import os
import re
import sys
import random

# Force color support by default (fixes zsh detection issues)
# Use --no-color flag or NO_COLOR=1 environment variable to disable
if not os.environ.get('NO_COLOR'):
    os.environ.setdefault('FORCE_COLOR', '1')

from dotenv import load_dotenv
from commitcraft import commit_craft, get_diff, CommitCraftInput, LModelOptions, EmojiConfig, LModel, filter_diff
from .config_handler import interactive_config
import typer
from typing import Optional
from typing_extensions import Annotated, Any
from rich.console import Console
from rich.theme import Theme

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
import rich.console
rich.console._console = console

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
    no_color: Annotated[
        bool,
        typer.Option(
            "--no-color", "-p", "--plain",
            help="Disable colored output (plain text only)"
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
        typer.Option(help="Return the [yellow]prompt[/yellow], don't send any request to the model")
    ] = False,

    provider:  Annotated[
        str,
        typer.Option(
            rich_help_panel='Model Config',
            help="Provider for the AI model (supported: [magenta]ollama[/magenta], [magenta]groq[/magenta], [magenta]google[/magenta], [magenta]openai[/magenta], [magenta]custom_openai_compatible[/magenta])"
        )
    ] = 'ollama',
    model: Annotated[
        Optional[str],
        typer.Option(
            rich_help_panel='Model Config',
            help="Model name (e.g., [cyan]gemma2[/cyan], [cyan]llama3.1:70b[/cyan])",
            show_default="ollama: [cyan]qwen3[/cyan], groq: [cyan]qwen/qwen3-32b[/cyan], google: [cyan]gemini-2.5-pro[/cyan], openai: [cyan]gpt-3.5-turbo[/cyan]"
        )
    ] = None,
    system_prompt: Annotated[Optional[str], typer.Option(rich_help_panel='Model Config', help="System prompt to guide the model")] = None,
    num_ctx: Annotated[Optional[int], typer.Option(rich_help_panel='Model Config', help="Context size for the model")] = None,
    temperature: Annotated[Optional[float], typer.Option(rich_help_panel='Model Config', help="Temperature for the model")] = None,
    max_tokens: Annotated[Optional[int], typer.Option(rich_help_panel='Model Config', help="Maximum number of tokens for the model")] = None,
    host: Annotated[
        Optional[str],
        typer.Option(
            rich_help_panel='Model Config',
            help="HTTP or HTTPS host for the provider, required for custom provider, not used for groq"
        )
    ] = None,
    show_thinking: Annotated[
        bool,
        typer.Option(
            rich_help_panel='Model Config',
            help="Show the model's thinking process if available"
        )
    ] = False,

    bug: Annotated[
        bool,
        typer.Option(
            rich_help_panel='Commit Clues',
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
    • [cyan]CUSTOM_API_KEY[/cyan] (for [magenta]custom_openai_compatible[/magenta] provider)
    • [cyan]OLLAMA_HOST[/cyan] (for [magenta]ollama[/magenta] provider, e.g., [dim]http://localhost:11434[/dim]; this can also be set directly in the configuration file).
    """
    if ctx.invoked_subcommand is None:
        # Handle color output
        if no_color:
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

        # Call the commit_craft function and print the result
        loading_message = random.choice(LOADING_MESSAGES)
        with err_console.status(loading_message, spinner="dots"):
            response = commit_craft(input, model_config, context_info, emoji_config, debug_prompt)
        
        # Process <think> tags
        think_pattern = r"<think>(.*?)</think>"
        think_match = re.search(think_pattern, response, re.DOTALL)
        
        if think_match:
            thinking_content = think_match.group(1).strip()
            # Remove the thinking part from the response
            response = re.sub(think_pattern, "", response, flags=re.DOTALL).strip()
            
            if show_thinking:
                err_console.print(f"[thinking_title]Thinking Process:[/thinking_title]")
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
def hook():
    """
    [dim]This Command is not implemented yet.[/dim]
    """
    raise NotImplementedError("This command is not implemented yet")

if __name__ == "__main__":
    app()
