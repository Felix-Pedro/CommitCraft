import json
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional

import toml
import typer
import yaml
from rich import print
from rich.prompt import Prompt

from .defaults import default


def validate_url(url: str) -> bool:
    if url == "ollama_cloud":
        return True
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def get_input_with_default(prompt_text, default_val):
    return typer.prompt(prompt_text, default=default_val)


def get_masked_input(prompt_text):
    return Prompt.ask(prompt_text, password=True)


def fetch_models(provider, api_key=None, host=None):
    try:
        if provider == "ollama":
            import ollama

            client_args = {"host": host}
            if api_key:
                client_args["headers"] = {"Authorization": f"Bearer {api_key}"}
            client = ollama.Client(**client_args)
            return [m["name"] for m in client.list()["models"]]
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
        elif provider == "openai_compatible":
            from openai import OpenAI

            client = OpenAI(api_key=api_key, base_url=host)
            return [m.id for m in client.models.list()]
    except Exception:
        # typer.secho(f"Debug: {e}", fg=typer.colors.RED)
        return []
    return []


def load_existing_config(base_dir):
    for ext in ["toml", "yaml", "json"]:
        config_path = base_dir / f"config.{ext}"
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    if ext == "toml":
                        return toml.load(f), ext
                    elif ext == "yaml":
                        return yaml.safe_load(f), ext
                    elif ext == "json":
                        return json.load(f), ext
            except Exception as e:
                print(f"[red]Error loading existing config: {e}[/red]")
    return {}, None


def configure_provider(
    provider_type: Optional[str] = None, nickname: Optional[str] = None, current_config: Optional[dict] = None
):
    """
    Helper to configure a provider (either main or named).
    Returns a tuple (config_dict, api_key_info_dict, env_var_name)
    """
    # Standard list for listing purposes
    KNOWN_PROVIDERS = [
        "ollama",
        "ollama_cloud",
        "openai",
        "google",
        "groq",
        "openai_compatible",
    ]

    current_config = current_config or {}

    # Pre-calculate defaults
    default_provider = current_config.get("provider", "ollama")

    if not provider_type:
        typer.echo(f"Known providers: {', '.join(KNOWN_PROVIDERS)}")
        while True:
            # If nickname is provided, the prompt should reflect that we are configuring that profile
            prompt_text = f"Provider Type for '{nickname}'" if nickname else "Provider"
            provider_input = typer.prompt(prompt_text, default=default_provider)

            # Map user input 'custom' to 'openai_compatible'
            if provider_input == "custom":
                provider_type = "openai_compatible"
                break

            # Check if input is a known standard provider
            if provider_input in KNOWN_PROVIDERS:
                provider_type = provider_input
                break

            # If not known, we handle it based on whether it's a named provider (nickname) scenario or not.
            # But here we are selecting the TYPE.
            # If the user typed something unknown, we warn and ask for clarification.

            print(
                f"[yellow]Warning: '{provider_input}' is not a standard provider type.[/yellow]"
            )

            # Offer selection between the flexible types: ollama or openai_compatible
            if typer.confirm(
                f"Is '{provider_input}' an OpenAI compatible provider?", default=True
            ):
                provider_type = "openai_compatible"
                break
            elif typer.confirm(
                f"Is '{provider_input}' an Ollama provider?", default=False
            ):
                provider_type = "ollama"
                break

            # If they say no to both, loop again? Or allow it as is (risky)?
            # Let's loop again to force a valid selection or valid type.
            print("[red]Please select a valid provider type.[/red]")

    # Handle ollama_cloud alias
    final_provider_type = provider_type
    if provider_type == "ollama_cloud":
        final_provider_type = "ollama"

    provider_config = {"provider": final_provider_type}

    # Host Prompt & Validation
    temp_host = None
    default_host = current_config.get("host")

    if final_provider_type == "ollama":
        if not default_host:
            default_host = (
                "ollama_cloud"
                if provider_type == "ollama_cloud"
                else "http://localhost:11434"
            )

        while True:
            temp_host = typer.prompt("Ollama Host URL", default=default_host)
            if validate_url(temp_host):
                provider_config["host"] = temp_host
                break
            print(
                "[red]Invalid URL. Please enter a valid HTTP/HTTPS URL or 'ollama_cloud'.[/red]"
            )

    elif final_provider_type == "openai_compatible":
        while True:
            temp_host = typer.prompt(
                "Host URL", default=default_host if default_host else ""
            )
            if validate_url(temp_host):
                provider_config["host"] = temp_host
                break
            print("[red]Invalid URL. Please enter a valid HTTP/HTTPS URL.[/red]")

    # Model Listing Option
    temp_api_key = None
    env_var_name = None

    if nickname:
        env_var_name = f"{nickname.upper()}_API_KEY"
        key_prompt_msg = f"API Key for {nickname} ({env_var_name})"
    else:
        key_map = {
            "openai": "OPENAI_API_KEY",
            "groq": "GROQ_API_KEY",
            "google": "GOOGLE_API_KEY",
            "openai_compatible": "CUSTOM_API_KEY",
            "ollama": "OLLAMA_API_KEY",
        }
        env_var_name = key_map.get(final_provider_type, "API_KEY")
        key_prompt_msg = f"{env_var_name}"

    # If existing config has api_key, we generally don't show it,
    # but we might want to check connectivity.

    models_list = []
    if typer.confirm(
        "Do you want to list available models? (May require API Key)", default=False
    ):
        if final_provider_type == "ollama":
            if typer.confirm(
                "Does your Ollama instance require an API Key?", default=False
            ):
                temp_api_key = get_masked_input(key_prompt_msg)
        elif (
            final_provider_type in KNOWN_PROVIDERS
            or final_provider_type == "openai_compatible"
        ):
            temp_api_key = get_masked_input(key_prompt_msg)

        models_list = fetch_models(
            final_provider_type, api_key=temp_api_key, host=temp_host
        )
        if models_list:
            print("[green]Available Models:[/green]")
            for i, m in enumerate(models_list, 1):
                typer.echo(f" {i}. {m}")
        else:
            print("[red]No models found or error occurred.[/red]")

    default_model = current_config.get("model", "qwen3")
    if not current_config.get("model"):
        if final_provider_type == "openai":
            default_model = "gpt-3.5-turbo"
        elif final_provider_type == "groq":
            default_model = "qwen/qwen3-32b"
        elif final_provider_type == "google":
            default_model = "gemini-1.5-pro"

    while True:
        model_name_input = get_input_with_default(
            "Model Name (or number)", default_model
        )

        # Check if input is a number and matches list
        if models_list and model_name_input.isdigit():
            idx = int(model_name_input)
            if 1 <= idx <= len(models_list):
                model_name = models_list[idx - 1]
                print(f"[cyan]Selected model: {model_name}[/cyan]")
            else:
                print("[red]Invalid model number.[/red]")
                continue
        else:
            model_name = model_name_input

        if model_name.strip():
            provider_config["model"] = model_name
            break
        print("[yellow]Model name cannot be empty.[/yellow]")

    api_key_info = None
    if temp_api_key:
        api_key_info = {"name": env_var_name, "value": temp_api_key}

    return provider_config, api_key_info, env_var_name


def interactive_config():
    print("[bold green]CommitCraft Configuration Wizard[/bold green]")

    # Scope
    while True:
        scope = typer.prompt(
            "Configuration Scope (project/global)", default="project"
        ).lower()
        if scope in ["project", "global"]:
            is_global = scope == "global"
            break
        print("[yellow]Invalid scope. Please choose 'project' or 'global'.[/yellow]")

    # Determine base directory
    if is_global:
        base_dir = Path(typer.get_app_dir("commitcraft"))
    else:
        base_dir = Path.cwd() / ".commitcraft"

    if not base_dir.exists():
        base_dir.mkdir(parents=True, exist_ok=True)

    # Load Existing Config
    existing_config, detected_format = load_existing_config(base_dir)
    is_edit_mode = bool(detected_format)

    if is_edit_mode:
        print(
            f"[cyan]Existing configuration found ({detected_format}). Entering edit mode.[/cyan]"
        )
        file_format = detected_format
    else:
        # Format
        while True:
            file_format = typer.prompt(
                "Configuration Format (toml/yaml/json)", default="toml"
            ).lower()
            if file_format in ["toml", "yaml", "json"]:
                break
            print(
                "[yellow]Invalid format. Please choose 'toml', 'yaml', or 'json'.[/yellow]"
            )

    # Initialize / Merge Config
    config = {
        "context": existing_config.get("context", {}),
        "models": existing_config.get("models", {}),
        "emoji": existing_config.get("emoji", {}),
        "providers": existing_config.get("providers", {}),
    }

    # Context
    print("\n[blue][Project Context][/blue]")
    if not is_global:
        config["context"]["project_name"] = get_input_with_default(
            "Project Name", config["context"].get("project_name", "")
        )
        config["context"]["project_language"] = get_input_with_default(
            "Project Language", config["context"].get("project_language", "")
        )
        config["context"]["project_description"] = get_input_with_default(
            "Project Description", config["context"].get("project_description", "")
        )

    # Commit Guidelines
    existing_guidelines = config["context"].get(
        "commit_guidelines", default["commit_guidelines"]
    )

    while True:
        prompt_msg = (
            "Commit Guidelines (default/custom/view/skip/keep)"
            if is_edit_mode
            else "Commit Guidelines (default/custom/view/skip)"
        )
        choice = typer.prompt(
            prompt_msg, default="keep" if is_edit_mode else "default"
        ).lower()

        if choice == "view":
            typer.echo(existing_guidelines)
        elif choice == "default":
            config["context"]["commit_guidelines"] = default["commit_guidelines"]
            break
        elif choice == "custom":
            config["context"]["commit_guidelines"] = typer.prompt(
                "Enter your custom commit guidelines", default=existing_guidelines
            )
            break
        elif choice == "skip":
            config["context"]["commit_guidelines"] = ""
            break
        elif choice == "keep" and is_edit_mode:
            break  # Keep existing
        else:
            print("[yellow]Invalid choice.[/yellow]")

    # Models (Main Default Provider)
    print("\n[blue][Default Model Settings][/blue]")

    env_keys_to_save = {}
    main_env_var = None

    should_configure_main = True

    # For project configs, offer to skip and use global settings
    if not is_global:
        if typer.confirm("Configure project-specific model settings? (No = use global settings)", default=True):
            should_configure_main = True
        else:
            should_configure_main = False
            config["models"] = {}  # Clear models section to use global
            print("[cyan]Project will use global model settings.[/cyan]")

    # For global configs or if user wants project-specific settings
    if should_configure_main:
        if is_edit_mode and config["models"]:
            if not typer.confirm("Edit default provider settings?", default=False):
                should_configure_main = False

    if should_configure_main:
        main_config, main_key_info, main_env_var = configure_provider(
            current_config=config["models"]
        )
        config["models"] = main_config
        if main_key_info:
            env_keys_to_save[main_key_info["name"]] = main_key_info["value"]
    else:
        # We need to know the env var name for the existing provider to offer saving it?
        # Maybe skip if not editing.
        pass

    # Named Providers
    print("\n[blue][Additional Providers][/blue]")

    # Edit existing named providers
    if config["providers"]:
        for nickname in list(config["providers"].keys()):
            # Using prompt instead of confirm to allow 'delete'
            action = typer.prompt(
                f"Manage provider profile '{nickname}'? (edit/delete/keep)",
                default="keep",
            ).lower()

            if action == "delete":
                del config["providers"][nickname]
                print(f"[yellow]Profile '{nickname}' marked for deletion.[/yellow]")
            elif action == "edit":
                p_config, p_key_info, p_env_var = configure_provider(
                    nickname=nickname, current_config=config["providers"][nickname]
                )
                config["providers"][nickname] = p_config
                if p_key_info:
                    env_keys_to_save[p_key_info["name"]] = p_key_info["value"]
            # else keep/skip

    if typer.confirm(
        "Do you want to add/configure additional providers?", default=False
    ):
        while True:
            KNOWN_PROVIDERS = [
                "ollama",
                "ollama_cloud",
                "openai",
                "google",
                "groq",
                "openai_compatible",
            ]
            typer.echo(f"Known providers: {', '.join(KNOWN_PROVIDERS)}")

            # 1. Ask for Provider Type
            p_type = typer.prompt("Select Provider Type", default="ollama")

            # Map 'custom' to 'openai_compatible' for user convenience if they type it
            if p_type == "custom":
                p_type = "openai_compatible"

            # Validation logic
            if p_type not in KNOWN_PROVIDERS:
                print(
                    f"[yellow]Warning: '{p_type}' is not a standard provider.[/yellow]"
                )
                if typer.confirm(
                    f"Is '{p_type}' an OpenAI compatible provider?", default=True
                ):
                    p_type = "openai_compatible"
                elif typer.confirm(f"Is '{p_type}' an Ollama provider?", default=False):
                    p_type = "ollama"
                else:
                    print("[red]Please select a valid provider type.[/red]")
                    continue

            # 2. Determine Nickname
            nickname = p_type  # Default nickname is the provider type

            if p_type in ["ollama", "ollama_cloud"]:
                # Always ask for nickname for ollama, defaulting to 'ollama'
                nickname = typer.prompt("Profile Nickname", default="ollama")
            elif p_type == "openai_compatible":
                # Must have a nickname for generic compatible providers
                nickname = typer.prompt(
                    "Profile Nickname (e.g. deepseek, litellm)",
                    default="openai_compatible",
                )

            # Check if exists
            current_p_config = config["providers"].get(nickname)
            if current_p_config:
                if not typer.confirm(
                    f"Profile '{nickname}' already exists. Overwrite?", default=True
                ):
                    continue

            # 3. Configure
            p_config, p_key_info, p_env_var = configure_provider(
                provider_type=p_type, nickname=nickname, current_config=current_p_config
            )
            config["providers"][nickname] = p_config

            if p_key_info:
                env_keys_to_save[p_key_info["name"]] = p_key_info["value"]

            if not p_key_info and p_env_var:
                if typer.confirm(
                    f"Do you want to save the API key for '{nickname}' ({p_env_var}) now?",
                    default=True,
                ):
                    val = get_masked_input(p_env_var)
                    env_keys_to_save[p_env_var] = val

            if not typer.confirm("Add another provider?", default=False):
                break

    # Emoji
    print("\n[blue][Emoji Settings][/blue]")
    if typer.confirm("Enable Emojis?", default=True):
        current_emoji_conv = config["emoji"].get("emoji_convention", "simple")
        while True:
            choice = typer.prompt(
                "Emoji Convention (simple/full/custom/view)", default=current_emoji_conv
            ).lower()
            if choice == "view":
                print("[green]Simple Convention:[/green]")
                typer.echo(default["emoji_guidelines"]["simple"])
                print("[green]Full Convention:[/green]")
                typer.echo(default["emoji_guidelines"]["full"])
            elif choice in ["simple", "full"]:
                config["emoji"]["emoji_convention"] = choice
                break
            elif choice == "custom":
                config["emoji"]["emoji_convention"] = typer.prompt(
                    "Enter your custom emoji convention", default=current_emoji_conv
                )
                break
            else:
                print("[yellow]Invalid choice.[/yellow]")

        config["emoji"]["emoji_steps"] = "single"
    else:
        config["emoji"] = {}  # Clear if disabled? or just don't use it.

    # Save Config
    file_path = base_dir / f"config.{file_format}"

    try:
        with open(file_path, "w") as f:
            if file_format == "toml":
                toml.dump(config, f)
            elif file_format == "yaml":
                yaml.dump(config, f)
            elif file_format == "json":
                json.dump(config, f, indent=4)
        print(f"[green]Configuration saved to {file_path}[/green]")
    except Exception as e:
        print(f"[red]Error saving configuration: {e}[/red]")

    # API Keys (.env) handling
    print("\n[blue][API Keys][/blue]")

    # Check if main key is missing from our collection but needed
    if main_env_var and main_env_var not in env_keys_to_save and should_configure_main:
        if typer.confirm(
            f"Do you want to configure the default API key ({main_env_var}) in .env?",
            default=True,
        ):
            val = get_masked_input(main_env_var)
            env_keys_to_save[main_env_var] = val

    if env_keys_to_save:
        print("[cyan]Keys to be saved:[/cyan]")
        for k in env_keys_to_save:
            typer.echo(f" - {k}")

        # Ask where to save
        choices = [".env", "CommitCraft.env", "skip"]
        save_choice = typer.prompt(
            "Where do you want to save these keys?", default=".env", show_choices=True
        )

        # Normalize input
        if save_choice not in choices:
            # Fallback or strict? Let's just try to match roughly or default to skip if invalid to be safe,
            # or better, loop? Typer prompt doesn't loop automatically with custom strings unless we use click Choice or similar.
            # But let's just handle text input.
            if "commitcraft" in save_choice.lower():
                save_choice = "CommitCraft.env"
            elif "env" in save_choice.lower():
                save_choice = ".env"
            else:
                save_choice = "skip"

        if save_choice != "skip":
            env_path = Path.cwd() / save_choice

            existing_lines = []
            if env_path.exists():
                with open(env_path, "r") as f:
                    existing_lines = f.readlines()

            with open(env_path, "a") as f:
                if existing_lines and not existing_lines[-1].endswith("\n"):
                    f.write("\n")
                for k, v in env_keys_to_save.items():
                    if not any(
                        line.strip().startswith(f"{k}=") for line in existing_lines
                    ):
                        f.write(f"{k}={v}\n")
                    else:
                        print(
                            f"[yellow]Key {k} already exists in {save_choice}, skipping.[/yellow]"
                        )

            print(f"[green]API keys process finished for {env_path}[/green]")
    else:
        print("[yellow]No API keys to save.[/yellow]")
