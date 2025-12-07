import typer
import os
from pathlib import Path
import toml
import json
import yaml
from .defaults import default
from urllib.parse import urlparse

def validate_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def get_input_with_default(prompt_text, default_val):
    return typer.prompt(prompt_text, default=default_val)

def fetch_models(provider, api_key=None, host=None):
    try:
        if provider == "ollama":
            import ollama
            client = ollama.Client(host=host)
            return [m['name'] for m in client.list()['models']]
        elif provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            return [m.id for m in client.models.list()]
        elif provider == "groq":
            from groq import Groq
            client = Groq(api_key=api_key)
            return [m.id for m in client.models.list().data]
        elif provider == "google":
             from google import genai
             client = genai.Client(api_key=api_key)
             return [m.name for m in client.models.list()]
        elif provider == "custom_openai_compatible":
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url=host)
            return [m.id for m in client.models.list()]
    except Exception as e:
        return [f"Error fetching models: {e}"]
    return []

def interactive_config():
    typer.secho("CommitCraft Configuration Wizard", fg=typer.colors.GREEN, bold=True)
    
    # Scope
    while True:
        scope = typer.prompt("Configuration Scope (project/global)", default="project").lower()
        if scope in ["project", "global"]:
            is_global = scope == "global"
            break
        typer.secho("Invalid scope. Please choose 'project' or 'global'.", fg=typer.colors.YELLOW)
    
    # Format
    while True:
        file_format = typer.prompt("Configuration Format (toml/yaml/json)", default="toml").lower()
        if file_format in ['toml', 'yaml', 'json']:
            break
        typer.secho("Invalid format. Please choose 'toml', 'yaml', or 'json'.", fg=typer.colors.YELLOW)

    config = {
        "context": {},
        "models": {},
        "emoji": {}
    }

    # Context
    typer.secho("\n[Project Context]", fg=typer.colors.BLUE)
    if not is_global:
        config['context']['project_name'] = get_input_with_default("Project Name", "")
        config['context']['project_language'] = get_input_with_default("Project Language", "")
        config['context']['project_description'] = get_input_with_default("Project Description", "")
    
    # Commit Guidelines
    while True:
        choice = typer.prompt("Commit Guidelines (default/custom/view/skip)", default="default").lower()
        if choice == "view":
            typer.echo(default['commit_guidelines'])
        elif choice == "default":
            config['context']['commit_guidelines'] = default['commit_guidelines']
            break
        elif choice == "custom":
            config['context']['commit_guidelines'] = typer.prompt("Enter your custom commit guidelines")
            break
        elif choice == "skip":
            config['context']['commit_guidelines'] = ""
            break
        else:
            typer.secho("Invalid choice.", fg=typer.colors.YELLOW)

    # Models
    typer.secho("\n[Model Settings]", fg=typer.colors.BLUE)
    
    KNOWN_PROVIDERS = ["ollama", "openai", "google", "groq", "custom_openai_compatible"]
    typer.echo(f"Known providers: {', '.join(KNOWN_PROVIDERS)}")
    
    while True:
        provider_input = typer.prompt("Provider", default="ollama")
        if provider_input == "custom":
             provider = "custom_openai_compatible"
             break
        elif provider_input not in KNOWN_PROVIDERS:
            typer.secho(f"Warning: '{provider_input}' is not a standard provider.", fg=typer.colors.YELLOW)
            if typer.confirm("Treat as custom OpenAI compatible provider?", default=True):
                provider = "custom_openai_compatible"
                # We save the custom name? The config structure expects specific provider keys or enums?
                # The LModel class uses enum. We must stick to enum values for internal config 'provider' field
                # but maybe we can note the custom name elsewhere or just treat it as custom_openai_compatible.
                # For now, we map to the enum value.
                break
            else:
                # If they insist on the name but it's not supported, the tool might fail later. 
                # Let's just allow it but warn.
                provider = provider_input
                break
        else:
            provider = provider_input
            break

    config['models']['provider'] = provider
    
    # Host Prompt & Validation
    temp_host = None
    if provider == "ollama":
        while True:
            temp_host = typer.prompt("Ollama Host URL", default="http://localhost:11434")
            if validate_url(temp_host):
                config['models']['host'] = temp_host
                break
            typer.secho("Invalid URL. Please enter a valid HTTP/HTTPS URL.", fg=typer.colors.RED)
            
    elif provider == "custom_openai_compatible":
         while True:
            temp_host = typer.prompt("Host URL")
            if validate_url(temp_host):
                config['models']['host'] = temp_host
                break
            typer.secho("Invalid URL. Please enter a valid HTTP/HTTPS URL.", fg=typer.colors.RED)

    # Model Listing Option
    temp_api_key = None
    if typer.confirm("Do you want to list available models? (May require API Key)", default=False):
        if provider in ["openai", "groq", "google", "custom_openai_compatible"]:
            key_name = {
                "openai": "OPENAI_API_KEY",
                "groq": "GROQ_API_KEY",
                "google": "GOOGLE_API_KEY",
                "custom_openai_compatible": "CUSTOM_API_KEY"
            }.get(provider, "API_KEY") # Fallback for unknown provider
            temp_api_key = typer.prompt(key_name, hide_input=True)
        
        models_list = fetch_models(provider, api_key=temp_api_key, host=temp_host)
        if models_list:
            typer.secho("Available Models:", fg=typer.colors.GREEN)
            for m in models_list:
                typer.echo(f" - {m}")
        else:
            typer.secho("No models found or error occurred.", fg=typer.colors.RED)

    default_model = "qwen3"
    if provider == "openai": default_model = "gpt-3.5-turbo"
    elif provider == "groq": default_model = "qwen/qwen3-32b"
    elif provider == "google": default_model = "gemini-1.5-pro"
    
    while True:
        model_name = get_input_with_default("Model Name", default_model)
        if model_name.strip():
            config['models']['model'] = model_name
            break
        typer.secho("Model name cannot be empty.", fg=typer.colors.YELLOW)

    # Emoji
    typer.secho("\n[Emoji Settings]", fg=typer.colors.BLUE)
    if typer.confirm("Enable Emojis?", default=True):
        while True:
            choice = typer.prompt("Emoji Convention (simple/full/custom/view)", default="simple").lower()
            if choice == "view":
                typer.secho("Simple Convention:", fg=typer.colors.GREEN)
                typer.echo(default['emoji_guidelines']['simple'])
                typer.secho("Full Convention:", fg=typer.colors.GREEN)
                typer.echo(default['emoji_guidelines']['full'])
            elif choice in ["simple", "full"]:
                config['emoji']['emoji_convention'] = choice
                break
            elif choice == "custom":
                config['emoji']['emoji_convention'] = typer.prompt("Enter your custom emoji convention")
                break
            else:
                typer.secho("Invalid choice.", fg=typer.colors.YELLOW)
        
        config['emoji']['emoji_steps'] = "single"

    # Save Config
    if is_global:
        base_dir = Path(typer.get_app_dir("commitcraft"))
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
            
            # Use previously entered key as default if available? 
            # Typer prompt doesn't strictly support pre-filling hidden input easily without default=...
            # But we can check if we have it.
            
            if provider == "openai":
                if temp_api_key:
                     if typer.confirm("Use the API key provided earlier?", default=True):
                         keys["OPENAI_API_KEY"] = temp_api_key
                     else:
                         keys["OPENAI_API_KEY"] = typer.prompt("OPENAI_API_KEY", hide_input=True)
                else:
                    keys["OPENAI_API_KEY"] = typer.prompt("OPENAI_API_KEY", hide_input=True)
            elif provider == "groq":
                if temp_api_key:
                     if typer.confirm("Use the API key provided earlier?", default=True):
                         keys["GROQ_API_KEY"] = temp_api_key
                     else:
                         keys["GROQ_API_KEY"] = typer.prompt("GROQ_API_KEY", hide_input=True)
                else:
                    keys["GROQ_API_KEY"] = typer.prompt("GROQ_API_KEY", hide_input=True)
            elif provider == "google":
                if temp_api_key:
                     if typer.confirm("Use the API key provided earlier?", default=True):
                         keys["GOOGLE_API_KEY"] = temp_api_key
                     else:
                         keys["GOOGLE_API_KEY"] = typer.prompt("GOOGLE_API_KEY", hide_input=True)
                else:
                    keys["GOOGLE_API_KEY"] = typer.prompt("GOOGLE_API_KEY", hide_input=True)
            elif provider == "custom_openai_compatible":
                if temp_api_key:
                     if typer.confirm("Use the API key provided earlier?", default=True):
                         keys["CUSTOM_API_KEY"] = temp_api_key
                     else:
                         keys["CUSTOM_API_KEY"] = typer.prompt("CUSTOM_API_KEY", hide_input=True)
                else:
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
