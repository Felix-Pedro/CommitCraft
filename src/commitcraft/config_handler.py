import typer
import os
from pathlib import Path
import toml
import json
import yaml

def get_input_with_default(prompt_text, default_val):
    return typer.prompt(prompt_text, default=default_val)

def interactive_config():
    typer.secho("CommitCraft Configuration Wizard", fg=typer.colors.GREEN, bold=True)
    
    # Scope
    scope = typer.prompt("Configuration Scope (project/global)", default="project")
    is_global = scope.lower() == "global"
    
    # Format
    file_format = typer.prompt("Configuration Format (toml/yaml/json)", default="toml").lower()
    if file_format not in ['toml', 'yaml', 'json']:
        typer.secho("Invalid format. Defaulting to toml.", fg=typer.colors.YELLOW)
        file_format = 'toml'

    config = {
        "context": {},
        "models": {},
        "emoji": {}
    }

    # Context
    typer.secho("\n[Project Context]", fg=typer.colors.BLUE)
    config['context']['project_name'] = get_input_with_default("Project Name", "")
    config['context']['project_language'] = get_input_with_default("Project Language", "")
    config['context']['project_description'] = get_input_with_default("Project Description", "")
    config['context']['commit_guidelines'] = get_input_with_default("Commit Guidelines", "")

    # Models
    typer.secho("\n[Model Settings]", fg=typer.colors.BLUE)
    provider = typer.prompt("Provider", default="ollama")
    config['models']['provider'] = provider
    
    default_model = "gemma2"
    if provider == "openai": default_model = "gpt-3.5-turbo"
    elif provider == "groq": default_model = "llama-3.1-70b-versatile"
    elif provider == "google": default_model = "gemini-1.5-pro"
    
    config['models']['model'] = get_input_with_default("Model Name", default_model)
    
    if provider == "custom_openai_compatible":
        config['models']['host'] = typer.prompt("Host URL")

    # Emoji
    typer.secho("\n[Emoji Settings]", fg=typer.colors.BLUE)
    if typer.confirm("Enable Emojis?", default=True):
        config['emoji']['emoji_convention'] = typer.prompt("Convention", default="simple")
        config['emoji']['emoji_steps'] = "single"

    # Save Config
    if is_global:
        base_dir = Path.home() / ".commitcraft"
    else:
        base_dir = Path.cwd() / ".commitcraft"
    
    if not base_dir.exists():
        base_dir.mkdir(parents=True, exist_ok=True)
        
    file_path = base_dir / f"config.{file_format}"
    
    write_mode = 'w'
    if file_path.exists():
        if not typer.confirm(f"File {file_path} exists. Overwrite?", default=False):
            typer.secho("Operation cancelled.", fg=typer.colors.RED)
            return
    
    try:
        with open(file_path, write_mode) as f:
            if file_format == 'toml':
                toml.dump(config, f)
            elif file_format == 'yaml':
                yaml.dump(config, f)
            elif file_format == 'json':
                json.dump(config, f, indent=4)
        typer.secho(f"Configuration saved to {file_path}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"Error saving configuration: {e}", fg=typer.colors.RED)
        
    # API Keys (.env) handling
    if provider in ["openai", "groq", "google", "custom_openai_compatible"]:
        typer.secho("\n[API Keys]", fg=typer.colors.BLUE)
        if typer.confirm("Do you want to configure API keys in a .env file?", default=True):
            env_path = Path.cwd() / ".env"
            keys = {}
            if provider == "openai":
                keys["OPENAI_API_KEY"] = typer.prompt("OPENAI_API_KEY", hide_input=True)
            elif provider == "groq":
                keys["GROQ_API_KEY"] = typer.prompt("GROQ_API_KEY", hide_input=True)
            elif provider == "google":
                keys["GOOGLE_API_KEY"] = typer.prompt("GOOGLE_API_KEY", hide_input=True)
            elif provider == "custom_openai_compatible":
                keys["CUSTOM_API_KEY"] = typer.prompt("CUSTOM_API_KEY", hide_input=True)
                
            if keys:
                # Simple .env writer that doesn't duplicate existing keys would be better,
                # but for now appends or writes.
                # Let's read existing to avoid duplicates if possible, or just append.
                # Append is safer than full overwrite.
                
                # Check if key exists
                existing_lines = []
                if env_path.exists():
                    with open(env_path, 'r') as f:
                        existing_lines = f.readlines()
                
                with open(env_path, 'a') as f:
                    if existing_lines and not existing_lines[-1].endswith('\n'):
                        f.write("\n")
                    for k, v in keys.items():
                        # Check if already present (rudimentary check)
                        if not any(line.strip().startswith(f"{k}=") for line in existing_lines):
                             f.write(f"{k}={v}\n")
                        else:
                             typer.secho(f"Key {k} already exists in .env, skipping.", fg=typer.colors.YELLOW)

                typer.secho(f"API keys process finished for {env_path}", fg=typer.colors.GREEN)
