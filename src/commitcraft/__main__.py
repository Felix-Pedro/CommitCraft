import os
from dotenv import load_dotenv
from commitcraft import commit_craft, get_diff, CommitCraftRequest, LModelOptions, EmojiConfig, Context, LModel
import argparse

load_dotenv()

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

def main():
    parser = argparse.ArgumentParser(description="CommitCraft - Generate commit messages using AI.")

    # Command-line arguments for overriding settings
    parser.add_argument('--provider', type=str, help="Provider for the AI model (supported are 'ollama')")
    parser.add_argument('--model', type=str, help="Model name (e.g., 'gemma2', 'llama3.1:70b')")
    parser.add_argument('--config-file', type=str, help="Path to the config file (TOML, YAML, or JSON)")
    parser.add_argument('--system-prompt', type=str, help="System prompt to guide the model")
    parser.add_argument('--num-ctx', type=int, help="Context size for the model")
    parser.add_argument('--temperature', type=float, help="Temperature for the model")
    parser.add_argument('--max-tokens', type=int, help="Maximum number of tokens for the model")
    parser.add_argument('--host', type=str, help="http or https host for the provider, in custom shall be the full api endpoint, not used for groq")


    # Parse known and unknown arguments
    args, unknown_args = parser.parse_known_args()

    # Get the git diff
    diff = get_diff()

    # Determine if the context file is provided or try to load the default
    config_file = args.config_file if args.config_file else None
    config = load_file(config_file) if config_file else load_config()

    context_info = Context(**config.get('context')) if config.get('context') else None
    emoji_config = EmojiConfig(**config.get('emoji')) if config.get('emoji') else EmojiConfig(emoji_steps='single', emoji_convention='simple')
    model_config = LModel(**config.get('models')) if config.get('models') else LModel()


    # Process unknown arguments as additional model options
    extra_model_options = {}
    for i in range(0, len(unknown_args), 2):
        key = unknown_args[i].lstrip('--').replace('-', '_')  # Remove '--' and normalize to snake_case
        if i + 1 < len(unknown_args):
            value = unknown_args[i + 1]
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    pass  # Keep as string if not convertible
            extra_model_options[key] = value

    # Construct the model options
    lmodel_options = LModelOptions(
        num_ctx=args.num_ctx if args.num_ctx else None,
        temperature=args.temperature if args.temperature else None,
        max_tokens=args.max_tokens if args.max_tokens else None,
        **extra_model_options  # Merge extra model options here
    )

    cli_options = lmodel_options.dict()
    config_options = model_config.options.dict() if model_config.options else {}
    model_options = { config : cli_options.get(config) if cli_options.get(config, False) else config_options.get(config) for config in set(list(cli_options.keys())+list(config_options.keys()))}

    model_config = LModel(
        provider=args.provider if args.provider else model_config.provider,
        model=args.model if args.model else None,
        system_prompt=args.system_prompt if args.system_prompt else model_config.system_prompt,
        host=args.host if args.host else model_config.host,
        options=LModelOptions(**model_options)
    )

    # Construct the request using provided arguments or defaults
    request = CommitCraftRequest(
        diff=diff,
        models=model_config,
        emoji=emoji_config,
        context=context_info
    )

    # Call the commit_craft function and print the result
    response = commit_craft(request)
    print(response)

if __name__ == '__main__':
    main()
