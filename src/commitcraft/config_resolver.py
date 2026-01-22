"""
Configuration Resolution Utilities

This module provides helper functions for resolving and merging CommitCraft configurations
from multiple sources (CLI args, project config, global config) following the priority:
CLI args > Project config > Global config > Defaults
"""

import os

from .CommitCraft import LModel, LModelOptions


def resolve_named_provider(
    provider_nickname: str,
    providers_config: dict,
) -> LModel:
    """
    Resolve a named provider configuration from the providers section.

    Args:
        provider_nickname: Nickname of the provider profile (e.g., "remote_ollama")
        providers_config: Dictionary of provider profiles from config file

    Returns:
        LModel instance configured from the named provider

    Raises:
        KeyError: If the nickname doesn't exist in providers_config
    """
    if provider_nickname not in providers_config:
        available = ", ".join(providers_config.keys())
        raise KeyError(
            f"Provider profile '{provider_nickname}' not found. "
            f"Available profiles: {available}"
        )

    provider_config = providers_config[provider_nickname]

    # Resolve API key from environment using nickname pattern
    env_key = f"{provider_nickname.upper()}_API_KEY"
    resolved_api_key = os.getenv(env_key)
    if resolved_api_key:
        provider_config["api_key"] = resolved_api_key

    return LModel(**provider_config)


def resolve_provider_config(
    provider_arg: str | None,
    config: dict,
) -> LModel:
    """
    Resolve provider configuration from CLI argument and config files.

    Determines whether the provider argument refers to:
    1. A named provider profile in the [providers] section
    2. A standard provider type (ollama, openai, etc.)

    Args:
        provider_arg: Provider name from CLI (or None)
        config: Full configuration dictionary

    Returns:
        Base LModel configuration (before CLI overrides)
    """
    providers_map = config.get("providers", {})

    # Check if provider_arg matches a named provider profile
    if provider_arg and provider_arg in providers_map:
        return resolve_named_provider(provider_arg, providers_map)

    # Fallback to standard [models] section or defaults
    models_config = config.get("models", {})
    return LModel(**models_config) if models_config else LModel()


def apply_cli_overrides(
    base_model: LModel,
    cli_args: dict,
) -> LModel:
    """
    Apply CLI argument overrides to a base model configuration.

    Only non-None CLI arguments are applied, preserving config file values
    for unspecified options.

    Args:
        base_model: Base LModel from config files
        cli_args: Dictionary of CLI arguments (may contain None values)

    Returns:
        New LModel with CLI overrides applied
    """
    # Extract CLI options
    cli_options = {
        "num_ctx": cli_args.get("num_ctx"),
        "temperature": cli_args.get("temperature"),
        "max_tokens": cli_args.get("max_tokens"),
    }

    # Merge with existing options
    base_options = base_model.options.model_dump() if base_model.options else {}
    merged_options = base_options.copy()

    for key, value in cli_options.items():
        if value is not None:
            merged_options[key] = value

    # Build new LModel with overrides
    return LModel(
        provider=cli_args.get("provider") or base_model.provider,
        model=cli_args.get("model") or base_model.model,
        system_prompt=cli_args.get("system_prompt") or base_model.system_prompt,
        host=cli_args.get("host") or base_model.host,
        api_key=base_model.api_key,  # API key never comes from CLI, preserve from config
        options=LModelOptions(**merged_options),
    )


def resolve_model_configuration(
    provider: str | None,
    model: str | None,
    system_prompt: str | None,
    host: str | None,
    num_ctx: int | None,
    temperature: float | None,
    max_tokens: int | None,
    config: dict,
) -> LModel:
    """
    Complete model configuration resolution pipeline.

    This is the main entry point for resolving model configuration.
    It handles:
    1. Named provider profiles vs standard providers
    2. Config file merging (project > global)
    3. CLI argument overrides

    Args:
        provider: CLI --provider argument
        model: CLI --model argument
        system_prompt: CLI --system-prompt argument
        host: CLI --host argument
        num_ctx: CLI --num-ctx argument
        temperature: CLI --temperature argument
        max_tokens: CLI --max-tokens argument
        config: Merged configuration dictionary

    Returns:
        Fully resolved LModel configuration
    """
    # Step 1: Resolve base configuration (named provider or standard provider)
    base_model = resolve_provider_config(provider, config)

    # Check if the provider arg was used to resolve a named profile
    # If so, we should NOT use it as a provider type override
    providers_map = config.get("providers", {})
    provider_override = provider
    if provider and provider in providers_map:
        provider_override = None

    # Step 2: Apply CLI overrides
    cli_args = {
        "provider": provider_override,
        "model": model,
        "system_prompt": system_prompt,
        "host": host,
        "num_ctx": num_ctx,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    return apply_cli_overrides(base_model, cli_args)
