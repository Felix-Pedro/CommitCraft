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
#
# CONTEXT_CHAR_TO_TOKEN_RATIO: Empirically determined through promptfoo testing
# across multiple Ollama models (Qwen, Gemma, Llama) with git diff content.
# The ratio of 2.64 means approximately 2.64 characters per token, which accounts for:
# - Mixed content (natural language commit messages + code diffs)
# - Special tokens and formatting overhead
# - Conservative buffer to avoid context overflow
#
# Note: As of CommitCraft 1.1.0+, tiktoken is a required dependency for accurate
# token counting. This fallback ratio is only used if tiktoken fails to load.
CONTEXT_CHAR_TO_TOKEN_RATIO = 2.64

# Minimum context size to ensure small diffs don't under-allocate
# Default: 1024, can be overridden by COMMITCRAFT_MIN_CONTEXT_SIZE
MIN_CONTEXT_SIZE = int(os.getenv("COMMITCRAFT_MIN_CONTEXT_SIZE", "1024"))

# Maximum context size to prevent memory issues
# Default: 128000 (128k), can be overridden by COMMITCRAFT_MAX_CONTEXT_SIZE
# Most Ollama models support 8K-128K context windows
MAX_CONTEXT_SIZE = int(os.getenv("COMMITCRAFT_MAX_CONTEXT_SIZE", "128000"))

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
        Calculate required context window size for Ollama models.

        Uses tiktoken for accurate token counting. The tiktoken library uses
        the cl100k_base encoding (GPT-3.5/4 tokenizer), which provides accurate
        results for most modern models (Qwen, Llama, Gemma, Mistral) as they
        all use similar BPE tokenization.

        If tiktoken fails to load for any reason, falls back to empirical
        character-to-token ratio of 2.64, determined through promptfoo testing
        across multiple Ollama models with git diff content.

        Note: Ollama API does not provide a tokenization endpoint, so pre-generation
        token counting must be done client-side. CommitCraft includes tiktoken as
        a required dependency to ensure accurate token counting.

        Args:
            system_prompt: System instruction text
            user_prompt: User input text (typically git diff)

        Returns:
            Calculated context size in tokens (bounded by MIN/MAX_CONTEXT_SIZE)
            Includes 60% buffer (50% for response + 10% overhead)
        """
        combined_text = system_prompt + user_prompt

        # Get bounds from options or fall back to module-level constants
        min_ctx_val = self.options.get("min_ctx") or MIN_CONTEXT_SIZE
        max_ctx_val = self.options.get("max_ctx") or MAX_CONTEXT_SIZE

        # Method 1: Try tiktoken if available (recommended for accuracy)
        try:
            import tiktoken

            # Use cl100k_base encoding (GPT-3.5/4 tokenizer)
            # This is close enough for most models (Qwen, Llama, Gemma, Mistral)
            # as they all use similar BPE tokenization
            encoding = tiktoken.get_encoding("cl100k_base")
            token_count = len(encoding.encode(combined_text))

            # Add 60% buffer: 50% for model response + 10% overhead
            # This buffer was empirically determined to prevent context overflow
            # while not over-allocating memory
            estimated = int(token_count * 1.6)

            return min(max(estimated, min_ctx_val), max_ctx_val)

        except ImportError:
            # tiktoken not installed - use character-based fallback
            pass
        except Exception:
            # tiktoken failed for some reason - fall back gracefully
            # This could happen with very large texts or encoding issues
            pass

        # Method 2: Character-based ratio estimation (fallback)
        # This provides reasonable estimates without additional dependencies
        input_len = len(combined_text)
        estimated_tokens = int(input_len * CONTEXT_CHAR_TO_TOKEN_RATIO)

        return min(max(estimated_tokens, min_ctx_val), max_ctx_val)


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
