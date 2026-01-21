"""
LLM Provider Registry and Implementations

This module implements a provider registry pattern for different LLM providers,
making it easy to add new providers and maintain existing ones.

Each provider implements a common interface while handling provider-specific
details like authentication, API endpoints, and option filtering.
"""

import os
from abc import ABC, abstractmethod
from typing import Optional

from .defaults import default


# Constants for context size calculation (used by Ollama)
# This ratio is empirical, based on typical token-to-character ratios for code diffs
CONTEXT_CHAR_TO_TOKEN_RATIO = 2.64
MIN_CONTEXT_SIZE = 1024
MAX_CONTEXT_SIZE = 128000

# Standard options supported by OpenAI-compatible APIs
OPENAI_COMPATIBLE_OPTIONS = ("top_p", "temperature", "max_tokens")


class LLMProviderError(Exception):
    """Base exception for provider-related errors."""

    pass


class APIKeyMissingError(LLMProviderError):
    """Raised when a required API key is missing."""

    pass


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All provider implementations must inherit from this class and implement
    the generate() method. Providers can optionally indicate whether they
    require an API key by setting requires_api_key.
    """

    # Subclasses should set this to True if API key is mandatory
    requires_api_key: bool = False

    # Subclasses can set this to specify the environment variable name for API key
    api_key_env_var: str | None = None

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        host: str | None = None,
        options: dict | None = None,
    ):
        """
        Initialize the provider.

        Args:
            model: Model name/identifier
            api_key: Optional API key for authentication
            host: Optional host URL for custom endpoints
            options: Optional model parameters (temperature, max_tokens, etc.)
        """
        self.model = model
        self.api_key = api_key
        self.host = host
        self.options = options or {}

        # Validate API key requirement
        if self.requires_api_key and not self.api_key:
            env_hint = (
                f" Set {self.api_key_env_var} environment variable"
                if self.api_key_env_var
                else ""
            )
            raise APIKeyMissingError(
                f"{self.__class__.__name__} requires an API key.{env_hint} "
                f"or provide it in your configuration file."
            )

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """
        Generate a response from the LLM.

        Args:
            system_prompt: System/instruction prompt for the model
            user_prompt: User input/query prompt

        Returns:
            Generated text response from the model

        Raises:
            LLMProviderError: If generation fails
        """
        pass

    def _filter_options(self, allowed_keys: tuple[str, ...]) -> dict:
        """
        Filter model options to only include allowed keys with non-None values.

        Args:
            allowed_keys: Tuple of option names that are valid for this provider

        Returns:
            Filtered dictionary of options
        """
        return {
            k: v for k, v in self.options.items() if k in allowed_keys and v is not None
        }


class OllamaProvider(LLMProvider):
    """
    Provider for local and remote Ollama instances.

    Supports:
    - Local instances (http://localhost:11434)
    - Remote instances with custom URLs
    - Optional API key authentication
    - Automatic context size calculation
    """

    requires_api_key = False  # Ollama can work without API key

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate response using Ollama's generate API."""
        import ollama

        # Build client arguments
        client_args = {}
        host_val = self.host or os.getenv("OLLAMA_HOST")
        if host_val:
            client_args["host"] = str(host_val)

        # Add API key if provided (for authenticated instances)
        ollama_api_key = self.api_key or os.getenv("OLLAMA_API_KEY")
        if ollama_api_key:
            client_args["headers"] = {"Authorization": f"Bearer {ollama_api_key}"}

        client = ollama.Client(**client_args)

        # Calculate context size if not provided or set to None/0
        if not self.options.get("num_ctx"):
            self.options["num_ctx"] = self._calculate_context_size(
                system_prompt, user_prompt
            )

        try:
            response = client.generate(
                model=self.model,
                system=system_prompt,
                prompt=user_prompt,
                options=self.options,
            )
            return response["response"]
        except Exception as e:
            raise LLMProviderError(f"Ollama generation failed: {e}") from e

    def _calculate_context_size(self, system_prompt: str, user_prompt: str) -> int:
        """
        Calculate required context window size based on input length.

        Uses an empirical character-to-token ratio to estimate the needed
        context size, with minimum and maximum bounds.

        Args:
            system_prompt: System instruction text
            user_prompt: User input text

        Returns:
            Estimated context size (number of tokens)
        """
        input_len = len(system_prompt) + len(user_prompt)
        num_ctx = int(
            min(
                max(input_len * CONTEXT_CHAR_TO_TOKEN_RATIO, MIN_CONTEXT_SIZE),
                MAX_CONTEXT_SIZE,
            )
        )
        return num_ctx


class OllamaCloudProvider(LLMProvider):
    """
    Provider for Ollama Cloud (https://ollama.com).

    Uses the chat API instead of generate API and requires API key authentication.
    Note: Cloud doesn't use num_ctx parameter.
    """

    requires_api_key = True
    api_key_env_var = "OLLAMA_API_KEY"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate response using Ollama Cloud's chat API."""
        import ollama

        # Cloud configuration
        client_args = {"host": "https://ollama.com"}

        # API key is required for cloud
        ollama_api_key = self.api_key or os.getenv("OLLAMA_API_KEY")
        if ollama_api_key:
            client_args["headers"] = {"Authorization": f"Bearer {ollama_api_key}"}

        client = ollama.Client(**client_args)

        # Build messages for chat API
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Filter out num_ctx (not supported by cloud)
        chat_options = {k: v for k, v in self.options.items() if k != "num_ctx"}

        try:
            response = client.chat(
                model=self.model,
                messages=messages,
                options=chat_options if chat_options else None,
            )
            return response["message"]["content"]
        except Exception as e:
            raise LLMProviderError(f"Ollama Cloud generation failed: {e}") from e


class GroqProvider(LLMProvider):
    """Provider for Groq's high-performance LLM API."""

    requires_api_key = True
    api_key_env_var = "GROQ_API_KEY"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate response using Groq's chat completions API."""
        from groq import Groq

        api_key = self.api_key or os.getenv("GROQ_API_KEY")
        client = Groq(api_key=api_key)

        # Filter to supported options
        filtered_options = self._filter_options(OPENAI_COMPATIBLE_OPTIONS)

        try:
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=self.model,
                stream=False,
                **filtered_options,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise LLMProviderError(f"Groq generation failed: {e}") from e


class GoogleProvider(LLMProvider):
    """Provider for Google's Gemini models."""

    requires_api_key = True
    api_key_env_var = "GOOGLE_API_KEY"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate response using Google's Gemini API."""
        from google import genai
        from google.genai import types

        api_key = self.api_key or os.getenv("GOOGLE_API_KEY")
        client = genai.Client(api_key=api_key)

        # Build config with system instruction
        google_config = {}
        if system_prompt:
            google_config["system_instruction"] = system_prompt

        # Map standard options to Google's parameter names
        if self.options.get("temperature") is not None:
            google_config["temperature"] = self.options["temperature"]
        if self.options.get("max_tokens") is not None:
            google_config["max_output_tokens"] = self.options["max_tokens"]
        if self.options.get("top_p") is not None:
            google_config["top_p"] = self.options["top_p"]

        try:
            response = client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(**google_config),
            )
            return response.text
        except Exception as e:
            raise LLMProviderError(f"Google generation failed: {e}") from e


class OpenAIProvider(LLMProvider):
    """Provider for OpenAI's GPT models."""

    requires_api_key = True
    api_key_env_var = "OPENAI_API_KEY"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate response using OpenAI's chat completions API."""
        from openai import OpenAI

        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key)

        # Filter to supported options
        filtered_options = self._filter_options(OPENAI_COMPATIBLE_OPTIONS)

        try:
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=self.model,
                stream=False,
                **filtered_options,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise LLMProviderError(f"OpenAI generation failed: {e}") from e


class OpenAICompatibleProvider(LLMProvider):
    """
    Provider for OpenAI-compatible APIs.

    This includes services like:
    - DeepSeek
    - LiteLLM
    - LocalAI
    - vLLM
    - Ollama (when accessed via OpenAI-compatible endpoint)
    - Any other service implementing OpenAI's API

    Note: Some compatible APIs don't require authentication. If your service
    requires an API key, set CUSTOM_API_KEY environment variable or provide
    it in your configuration.
    """

    requires_api_key = False  # Some compatible APIs don't require keys
    api_key_env_var = "CUSTOM_API_KEY"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate response using OpenAI-compatible API."""
        from openai import OpenAI

        # API key may or may not be required depending on the service
        api_key = self.api_key or os.getenv("CUSTOM_API_KEY")

        # Try to create client - let it fail naturally if API key is required but missing
        # Don't use a dummy key as that could leak information to third-party APIs
        try:
            client = OpenAI(
                api_key=api_key,  # None is acceptable for some services
                base_url=str(self.host),
            )
        except Exception as e:
            # If client creation fails due to missing API key, provide helpful message
            if "api_key" in str(e).lower():
                raise APIKeyMissingError(
                    f"The OpenAI-compatible service at {self.host} requires an API key. "
                    f"Set CUSTOM_API_KEY environment variable or provide api_key in configuration."
                ) from e
            raise LLMProviderError(
                f"Failed to initialize OpenAI-compatible client: {e}"
            ) from e

        # Filter to supported options
        filtered_options = self._filter_options(OPENAI_COMPATIBLE_OPTIONS)

        try:
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=self.model,
                stream=False,
                **filtered_options,
            )
            return response.choices[0].message.content
        except Exception as e:
            # Check if the error is authentication-related
            error_str = str(e).lower()
            if any(
                keyword in error_str
                for keyword in ["unauthorized", "401", "api key", "authentication"]
            ):
                raise APIKeyMissingError(
                    f"Authentication failed for {self.host}. "
                    f"The service requires an API key. Set CUSTOM_API_KEY environment variable "
                    f"or provide api_key in your configuration."
                ) from e
            raise LLMProviderError(f"OpenAI-compatible generation failed: {e}") from e


# Provider Registry
# Maps provider names to their implementation classes
PROVIDER_REGISTRY: dict[str, type[LLMProvider]] = {
    "ollama": OllamaProvider,
    "ollama_cloud": OllamaCloudProvider,
    "groq": GroqProvider,
    "google": GoogleProvider,
    "openai": OpenAIProvider,
    "openai_compatible": OpenAICompatibleProvider,
}


def get_provider(
    provider_name: str,
    model: str,
    api_key: str | None = None,
    host: str | None = None,
    options: dict | None = None,
) -> LLMProvider:
    """
    Factory function to create a provider instance.

    Args:
        provider_name: Name of the provider (e.g., "ollama", "openai")
        model: Model name/identifier
        api_key: Optional API key
        host: Optional host URL
        options: Optional model parameters

    Returns:
        Configured provider instance

    Raises:
        LLMProviderError: If provider name is not recognized
        APIKeyMissingError: If required API key is missing
    """
    provider_class = PROVIDER_REGISTRY.get(provider_name)

    if not provider_class:
        available = ", ".join(PROVIDER_REGISTRY.keys())
        raise LLMProviderError(
            f"Unknown provider: {provider_name}. Available providers: {available}"
        )

    return provider_class(
        model=model,
        api_key=api_key,
        host=host,
        options=options,
    )
