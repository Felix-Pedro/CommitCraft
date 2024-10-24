import os
from dotenv import load_dotenv
from commitcraft import commit_craft, get_diff, CommitCraftInput, LModelOptions, EmojiConfig, LModel, filter_diff
import typer
from typing import Optional
from typing_extensions import Annotated, Any

app = typer.Typer()

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

def find_default_file(filename):
    """Finds the default file in the .commitcraft directory."""
    context_dir = './.commitcraft'
    extensions = ['toml', 'yaml', 'yml', 'json']
    for ext in extensions:
        file_path = os.path.join(context_dir, f'{filename}.{ext}')
        if os.path.exists(file_path):
            return file_path
    return None

def load_config():
    """Load configuration from either separate files or a single config file."""
    config_file = './.commitcraft/config'
    if os.path.exists(config_file):
        return load_file(config_file)

    # Try to load from individual files if config does not exist
    context_file = find_default_file('context')
    models_file = find_default_file('models')
    emoji_file = find_default_file('emoji')
    config_file = find_default_file('config')

    context = load_file(context_file) if context_file else None
    models = load_file(models_file) if models_file else None
    emoji = load_file(emoji_file) if emoji_file else None

    if not context_file and not models_file and not emoji_file and config_file:
       config =  load_file(config_file)
       return config

    return {
        "context": context,
        "models": models,
        "emoji": emoji
    }

@app.callback(invoke_without_command=True)
def main(
    config_file: Annotated[
        Optional[str],
        typer.Option(help="Path to the config file (TOML, YAML, or JSON)", show_default='tries to open .commitcraft folder in the root of the repo')
    ] = None,
    ignore: Annotated[
        Optional[str],
        typer.Option(help="files or file patterns to ignore on the message generation process comma separated", show_default='tries to open .commitcraft/.ignore file of the repo')
    ] = None,
    debug_prompt: Annotated[
        bool,
        typer.Option(help="Return the prompt, don't send any request to the model")
    ] = False,

    provider:  Annotated[
        str,
        typer.Option(rich_help_panel='Model Config', help="Provider for the AI model (supported values are 'ollama', 'groq', 'google', 'openai' and 'custom_openai_compatible')")
    ] = 'ollama',
    model: Annotated[
        Optional[str],
        typer.Option(
            rich_help_panel='Model Config',
            help="Model name (e.g., 'gemma2', 'llama3.1:70b')",
            show_default="ollama: 'gemma2', groq: 'llama-3.1-70b-versatile', google: 'gemini-1,5-pro', openai: 'gpt-3.5-turbo'"
        )
    ] = None,
    system_prompt: Annotated[Optional[str], typer.Option(rich_help_panel='Model Config', help="System prompt to guide the model")] = None,
    num_ctx: Annotated[Optional[int], typer.Option(rich_help_panel='Model Config', help="Context size for the model")] = None,
    temperature: Annotated[Optional[float], typer.Option(rich_help_panel='Model Config', help="Temperature for the model")] = None,
    max_tokens: Annotated[Optional[int], typer.Option(rich_help_panel='Model Config', help="Maximum number of tokens for the model")] = None,
    host: Annotated[Optional[str], typer.Option(rich_help_panel='Model Config', help="HTTP or HTTPS host for the provider, required for custom provider, not used for groq")] = None,

    bug: Annotated[bool, typer.Option(rich_help_panel='Commit Clues', help="Indicates to the model that the commit fix a bug, not necessary if using --bug-desc") ] = False,
    bug_desc: Annotated[Optional[str], typer.Option(rich_help_panel='Commit Clues', help="Describes the bug fixed")] = None,
    feat: Annotated[bool, typer.Option(rich_help_panel='Commit Clues', help="Indicates to the model that the commit adds a feature, not necessary if using --feat-desc") ] = False,
    feat_desc: Annotated[Optional[str], typer.Option(rich_help_panel='Commit Clues', help="Describes the feature added")] = None,
    docs: Annotated[bool, typer.Option(rich_help_panel='Commit Clues', help="Indicates to the model that the commit focous on documentation, not necessary if using --docs-desc") ] = False,
    docs_desc: Annotated[Optional[str], typer.Option(rich_help_panel='Commit Clues', help="Describes the documentation change/addition")] = None,
    refact: Annotated[bool, typer.Option(rich_help_panel='Commit Clues', help="Indicates to the model that the commit focous on refacotoring, not necessary if using --refact-desc") ] = False,
    refact_desc: Annotated[Optional[str], typer.Option(rich_help_panel='Commit Clues', help="Describes refactoring")] = None,
    context_clue: Annotated[Optional[str], typer.Option(rich_help_panel='Commit Clues', help="Gives the model a custom clue of the current commit")] = None,

     project_name: Annotated[Optional[str], typer.Option(rich_help_panel='Default Context', help="Your Project name")] = None,
     project_language: Annotated[Optional[str], typer.Option(rich_help_panel='Default Context', help="Your Project language")] = None,
     project_description: Annotated[Optional[str], typer.Option(rich_help_panel='Default Context', help="Your Project description")] = None,
     commit_guide: Annotated[Optional[str], typer.Option(rich_help_panel='Default Context', help="Your Project Commit Guidelines")] = None

):
    """
    Generates a commit message based on the result of `git diff --staged -M` and your clues, via the LLM you choose.
    """
    load_dotenv(os.path.join(os.getcwd(), ".env"))

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
    model_config = LModel(**config.get('models')) if config.get('models') else LModel()

    # Process unknown arguments as additional model options
    # extra_model_options = {}
    # for i in range(0, len(unknown_args), 2):
    #    key = unknown_args[i].lstrip('--').replace('-', '_')  # Remove '--' and normalize to snake_case
    #    if i + 1 < len(unknown_args):
    #        value = unknown_args[i + 1]
    #        try:
        #            value = int(value)
    #        except ValueError:
        #            try:
            #                value = float(value)
    #            except ValueError:
        #                pass  # Keep as string if not convertible
        #        extra_model_options[key] = value

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
        provider=provider if provider else model_config.provider,
        model=model if model else None,
        system_prompt=system_prompt if system_prompt else model_config.system_prompt,
        host=host if host else model_config.host,
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
    response = commit_craft(input, model_config, context_info, emoji_config, debug_prompt)
    typer.echo(response)

@app.command('init')
def init():
    """
    This Command is not implemented yet.
    """
    raise NotImplementedError("This command is not implemented yet")

@app.command('config')
def config():
    """
    This Command is not implemented yet.
    """
    raise NotImplementedError("This command is not implemented yet")

if __name__ == "__main__":
    app()
