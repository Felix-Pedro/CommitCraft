"""
LLM Provider Registry and Implementations

This module implements a provider registry pattern for different LLM providers,
making it easy to add new providers and maintain existing ones.

Each provider implements a common interface while handling provider-specific
details like authentication, API endpoints, and option filtering.
"""

import os
import warnings
from abc import ABC, abstractmethod


# Constants for context size calculation (used by Ollama)
#
# CONTEXT_CHAR_TO_TOKEN_RATIO: Empirically determined through promptfoo testing
# across multiple Ollama models (Qwen, Gemma, Llama) with git diff content.
# The ratio of 2.64 means approximately 2.64 characters per token, which accounts for:
# - Mixed content (natural language commit messages + code diffs)
# - Special tokens and formatting overhead
# - Conservative buffer to avoid context overflow
#
# Methodology:
# We tested various diff sizes against tiktoken's cl100k_base encoding and compared
# character counts to token counts. The average ratio was around 3.5 chars/token
# for code, but closer to 2.5-3.0 for mixed diff content. 2.64 provides a safe
# lower bound estimation when tiktoken is unavailable.
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


class CommitCraftWarning(UserWarning):
    """Base warning for CommitCraft."""

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

    # Subclasses should set this to match the provider registry name
    provider_name: str = "unknown"

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        host: str | None = None,
        options: dict | None = None,
        nickname: str | None = None,
    ):
        """
        Initialize the provider.

        Args:
            model: Model name/identifier
            api_key: Optional API key for authentication
            host: Optional host URL for custom endpoints
            options: Optional model parameters (temperature, max_tokens, etc.)
            nickname: Optional user-defined name for this provider instance
        """
        self.model = model
        self.api_key = api_key
        self.host = host
        self.options = options or {}
        self.nickname = nickname

        # Validate API key requirement
        # Check if api_key is provided OR if it's available in environment
        if not self.api_key and self.api_key_env_var:
            # Try to get from environment variable as fallback
            env_api_key = os.getenv(self.api_key_env_var)
            if env_api_key:
                self.api_key = env_api_key

        # If strict requirement and still no key, raise error
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

    def calculate_usage(self, system_prompt: str, user_prompt: str) -> dict:
        """
        Calculate token usage for the request.

        Args:
            system_prompt: System/instruction prompt
            user_prompt: User input prompt

        Returns:
            Dictionary containing token usage information
        """
        system_tokens = self._count_tokens(system_prompt)
        user_tokens = self._count_tokens(user_prompt)
        token_count = system_tokens + user_tokens

        result = {
            "token_count": token_count,
            "system_prompt_tokens": system_tokens,
            "user_prompt_tokens": user_tokens,
            "model": self.model,
            "provider": self.nickname if self.nickname else self.provider_name,
        }

        # Add host URL if present (for custom endpoints)
        if self.host:
            result["host"] = self.host

        return result

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken or fallback estimation.
        """
        try:
            import tiktoken

            # Use cl100k_base encoding (standard for modern LLMs)
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except (ImportError, Exception):
            # Fallback to character estimation
            return int(len(text) / CONTEXT_CHAR_TO_TOKEN_RATIO)

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
    provider_name = "ollama"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate response using Ollama's generate API."""
        import ollama

        # Build client arguments
        client_args = {}
        host_val = self.host or os.getenv("OLLAMA_HOST")
        if host_val:
            client_args["host"] = str(host_val)

        # Add API key if provided (for authenticated instances)
        if self.api_key:
            client_args["headers"] = {"Authorization": f"Bearer {self.api_key}"}
        elif os.getenv("OLLAMA_API_KEY"):
            # Fallback for non-strict API key (OllamaProvider requires_api_key=False)
            # but user might have set it in env var anyway
            client_args["headers"] = {
                "Authorization": f"Bearer {os.getenv('OLLAMA_API_KEY')}"
            }

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

    def calculate_usage(self, system_prompt: str, user_prompt: str) -> dict:
        """Calculate token usage and context size for Ollama."""
        usage = super().calculate_usage(system_prompt, user_prompt)

        # Calculate context size using the same logic as generate()
        context_size = self._calculate_context_size(system_prompt, user_prompt)

        usage.update(
            {
                "context_size": context_size,
                "context_utilization": f"{(usage['token_count'] / context_size) * 100:.1f}%",
            }
        )
        return usage

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

        token_count = self._count_tokens(combined_text)

        # Add 60% buffer: 50% for model response + 10% overhead
        estimated = int(token_count * 1.6)

        return min(max(estimated, min_ctx_val), max_ctx_val)


class OllamaCloudProvider(LLMProvider):
    """
    Provider for Ollama Cloud (https://ollama.com).

    Uses the chat API instead of generate API and requires API key authentication.
    Note: Cloud doesn't use num_ctx parameter.
    """

    requires_api_key = True
    api_key_env_var = "OLLAMA_API_KEY"
    provider_name = "ollama_cloud"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate response using Ollama Cloud's chat API."""
        import ollama

        # Cloud configuration
        client_args = {"host": "https://ollama.com"}

        # API key is required and guaranteed by __init__
        client_args["headers"] = {"Authorization": f"Bearer {self.api_key}"}

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
    provider_name = "groq"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate response using Groq's chat completions API."""
        from groq import Groq

        client = Groq(api_key=self.api_key)

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
    provider_name = "google"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate response using Google's Gemini API."""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)

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

    def calculate_usage(self, system_prompt: str, user_prompt: str) -> dict:
        """Calculate token usage for Google using native API."""
        from google import genai

        # Use resolved API key
        api_key = self.api_key

        try:
            client = genai.Client(api_key=api_key)

            # Normalize model name for Google SDK
            model_name = self.model
            if not model_name.startswith("models/"):
                model_name = f"models/{model_name}"

            # Count system prompt tokens separately
            system_tokens = 0
            if system_prompt:
                system_response = client.models.count_tokens(
                    model=model_name,
                    contents=[system_prompt],
                )
                system_tokens = system_response.total_tokens or 0

            # Count user prompt tokens separately
            user_response = client.models.count_tokens(
                model=model_name,
                contents=[user_prompt],
            )
            user_tokens = user_response.total_tokens or 0

            result = {
                "token_count": system_tokens + user_tokens,
                "system_prompt_tokens": system_tokens,
                "user_prompt_tokens": user_tokens,
                "model": self.model,
                "provider": self.nickname if self.nickname else self.provider_name,
            }

            # Add host URL if present
            if self.host:
                result["host"] = self.host

            return result
        except Exception as e:
            warnings.warn(
                f"Failed to use native Google token counting for model '{self.model}'. "
                f"Falling back to tiktoken estimation. Error: {e}",
                CommitCraftWarning,
            )
            # Fallback to tiktoken/heuristic if API fails (e.g. auth error during dry-run)
            return super().calculate_usage(system_prompt, user_prompt)


class AnthropicProvider(LLMProvider):
    """Provider for Anthropic's Claude models."""

    requires_api_key = True
    api_key_env_var = "ANTHROPIC_API_KEY"
    provider_name = "anthropic"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate response using Anthropic's Messages API."""
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)

        # Filter to supported options
        # Anthropic supports: max_tokens, temperature, top_p (and others)
        filtered_options = self._filter_options(("max_tokens", "temperature", "top_p"))

        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=filtered_options.get(
                    "max_tokens", 1024
                ),  # Required parameter
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                **{k: v for k, v in filtered_options.items() if k != "max_tokens"},
            )
            return response.content[0].text
        except Exception as e:
            raise LLMProviderError(f"Anthropic generation failed: {e}") from e

    def calculate_usage(self, system_prompt: str, user_prompt: str) -> dict:
        """Calculate token usage using Anthropic's native count_tokens API.

        Uses a single-character placeholder workaround to get accurate token counts
        for system and user prompts separately, since Anthropic's API doesn't allow
        empty content in messages or system fields.
        """
        import anthropic

        try:
            client = anthropic.Anthropic(api_key=self.api_key)

            # Count system prompt tokens using a single-char placeholder for user message
            # Anthropic API doesn't allow empty content, so we use " " and subtract 1
            system_response = client.messages.count_tokens(
                model=self.model,
                system=system_prompt,
                messages=[{"role": "user", "content": " "}],  # Single space placeholder
            )
            system_tokens = max(
                0, system_response.input_tokens - 1
            )  # Subtract placeholder

            # Count user prompt tokens using a single-char placeholder for system
            user_response = client.messages.count_tokens(
                model=self.model,
                system=" ",  # Single space placeholder
                messages=[{"role": "user", "content": user_prompt}],
            )
            user_tokens = max(0, user_response.input_tokens - 1)  # Subtract placeholder

            result = {
                "token_count": system_tokens + user_tokens,
                "system_prompt_tokens": system_tokens,
                "user_prompt_tokens": user_tokens,
                "model": self.model,
                "provider": self.nickname if self.nickname else self.provider_name,
            }

            # Add host URL if present (though rarely used with Anthropic)
            if self.host:
                result["host"] = self.host

            return result
        except Exception as e:
            warnings.warn(
                f"Failed to use native Anthropic token counting for model '{self.model}'. "
                f"Falling back to tiktoken estimation. Error: {e}",
                CommitCraftWarning,
            )
            # Fallback to tiktoken if API fails (e.g. auth error during dry-run)
            return super().calculate_usage(system_prompt, user_prompt)


class OpenAIProvider(LLMProvider):
    """Provider for OpenAI's GPT models."""

    requires_api_key = True
    api_key_env_var = "OPENAI_API_KEY"
    provider_name = "openai"

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate response using OpenAI's chat completions API."""
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)

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
    provider_name = "openai_compatible"

    def calculate_usage(self, system_prompt: str, user_prompt: str) -> dict:
        """Calculate token usage, using native tokenizers for Gemini/Claude if applicable."""
        # If it's a Claude model being accessed via OpenAI-compatible proxy (LiteLLM, OpenRouter),
        # try to use native Anthropic token counting
        if "claude" in self.model.lower():
            try:
                import anthropic

                # Use ANTHROPIC_API_KEY for counting even if using CUSTOM_API_KEY for generation
                anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
                if anthropic_api_key:
                    client = anthropic.Anthropic(api_key=anthropic_api_key)

                    # Normalize model name for Anthropic SDK
                    # Handle cases like 'anthropic/claude-3-5-sonnet' or 'claude-3-5-sonnet-20241022'
                    model_name = self.model
                    if "/" in model_name:
                        # Extract the actual model name after the slash
                        model_name = model_name.split("/")[-1]

                    # Count system prompt tokens
                    system_response = client.messages.count_tokens(
                        model=model_name,
                        system=system_prompt,
                        messages=[{"role": "user", "content": ""}],
                    )
                    system_tokens = system_response.input_tokens

                    # Count user prompt tokens
                    user_response = client.messages.count_tokens(
                        model=model_name,
                        system="",
                        messages=[{"role": "user", "content": user_prompt}],
                    )
                    user_tokens = user_response.input_tokens

                    result = {
                        "token_count": system_tokens + user_tokens,
                        "system_prompt_tokens": system_tokens,
                        "user_prompt_tokens": user_tokens,
                        "model": self.model,
                        "provider": self.nickname
                        if self.nickname
                        else self.provider_name,
                    }

                    # Add host URL if present
                    if self.host:
                        result["host"] = self.host

                    return result
            except Exception as e:
                warnings.warn(
                    f"Failed to use native Anthropic token counting for model '{self.model}'. "
                    f"Falling back to tiktoken estimation. Error: {e}",
                    CommitCraftWarning,
                )
                # Fallback to tiktoken if Anthropic SDK fails or key missing
                pass

        # If it's a Gemini model being accessed via OpenAI proxy, try to use native counting
        if "gemini" in self.model.lower():
            try:
                from google import genai

                # Use GOOGLE_API_KEY for counting even if using CUSTOM_API_KEY for generation
                google_api_key = os.getenv("GOOGLE_API_KEY")
                if google_api_key:
                    client = genai.Client(api_key=google_api_key)

                    # Normalize model name for Google SDK (e.g., 'gemini/gemini-pro' -> 'models/gemini-pro')
                    model_name = self.model
                    if "/" in model_name:
                        # Handle cases like 'gemini/gemini-pro' or 'google/gemini-pro'
                        # but preserve 'models/gemini-pro' if already present
                        parts = model_name.split("/")
                        if parts[0] != "models":
                            model_name = parts[-1]

                    if not model_name.startswith("models/"):
                        model_name = f"models/{model_name}"

                    # Count system prompt tokens
                    system_tokens = 0
                    if system_prompt:
                        system_response = client.models.count_tokens(
                            model=model_name,
                            contents=[system_prompt],
                        )
                        system_tokens = system_response.total_tokens or 0

                    # Count user prompt tokens
                    user_response = client.models.count_tokens(
                        model=model_name,
                        contents=[user_prompt],
                    )
                    user_tokens = user_response.total_tokens or 0

                    result = {
                        "token_count": system_tokens + user_tokens,
                        "system_prompt_tokens": system_tokens,
                        "user_prompt_tokens": user_tokens,
                        "model": self.model,
                        "provider": self.nickname
                        if self.nickname
                        else self.provider_name,
                    }

                    # Add host URL if present
                    if self.host:
                        result["host"] = self.host

                    return result
            except Exception as e:
                warnings.warn(
                    f"Failed to use native Google token counting for model '{self.model}'. "
                    f"Falling back to tiktoken estimation. Error: {e}",
                    CommitCraftWarning,
                )
                # Fallback to tiktoken if Google SDK fails or key missing
                pass

        return super().calculate_usage(system_prompt, user_prompt)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate response using OpenAI-compatible API."""
        from openai import OpenAI

        # API key may or may not be required depending on the service
        # self.api_key is already resolved in __init__ if required, or tried from env
        # If it's None here, it means it wasn't strictly required (OpenAICompatibleProvider.requires_api_key=False)
        # and wasn't found in env.
        api_key = self.api_key

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
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "openai_compatible": OpenAICompatibleProvider,
}


def get_provider(
    provider_name: str,
    model: str,
    api_key: str | None = None,
    host: str | None = None,
    options: dict | None = None,
    nickname: str | None = None,
) -> LLMProvider:
    """
    Factory function to create a provider instance.

    Args:
        provider_name: Name of the provider (e.g., "ollama", "openai")
        model: Model name/identifier
        api_key: Optional API key
        host: Optional host URL
        options: Optional model parameters
        nickname: Optional user-defined name for this provider instance

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
        nickname=nickname,
    )
