import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from commitcraft.providers import GoogleProvider, OpenAICompatibleProvider

# Define mocks
mock_types = MagicMock()


class MockCountTokensConfig:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class MockGenerateContentConfig:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


mock_types.CountTokensConfig = MockCountTokensConfig
mock_types.GenerateContentConfig = MockGenerateContentConfig

mock_genai = MagicMock()
mock_genai.types = mock_types


@pytest.fixture
def mock_google_modules():
    """Patches google.genai modules in sys.modules."""
    # Create a fresh mock client for each test
    mock_client_instance = MagicMock()
    mock_genai.Client.return_value = mock_client_instance

    mock_google = MagicMock()
    mock_google.genai = mock_genai

    # Patch dictionary
    modules_to_patch = {
        "google": mock_google,
        "google.genai": mock_genai,
        "google.genai.types": mock_types,
    }

    with patch.dict(sys.modules, modules_to_patch):
        yield mock_genai, mock_client_instance


class TestGoogleProvider:
    def test_calculate_usage_uses_count_tokens_config(self, mock_google_modules):
        """Verify that calculate_usage uses CountTokensConfig."""
        mock_genai_mod, mock_client = mock_google_modules

        mock_response = MagicMock()
        mock_response.total_tokens = 100
        mock_client.models.count_tokens.return_value = mock_response

        provider = GoogleProvider(
            model="gemini-pro", api_key="fake-key", options={"temperature": 0.5}
        )

        # Execute
        result = provider.calculate_usage("System prompt", "User prompt")

        # Verify
        assert result["token_count"] == 100

        # Check call arguments
        args, kwargs = mock_client.models.count_tokens.call_args
        assert kwargs["model"] == "models/gemini-pro"
        # Verify contents has both prompts
        assert kwargs["contents"] == ["System prompt", "User prompt"]

        # Verify no config is passed for system instruction (since it's in contents)
        assert "config" not in kwargs

    def test_generate_uses_generate_content_config(self, mock_google_modules):
        """Verify that generate uses GenerateContentConfig."""
        mock_genai_mod, mock_client = mock_google_modules

        mock_response = MagicMock()
        mock_response.text = "Generated commit"
        mock_client.models.generate_content.return_value = mock_response

        provider = GoogleProvider(
            model="gemini-pro", api_key="fake-key", options={"temperature": 0.5}
        )

        # Execute
        result = provider.generate("System prompt", "User prompt")

        # Verify
        assert result == "Generated commit"

        # Check call arguments
        args, kwargs = mock_client.models.generate_content.call_args
        assert kwargs["model"] == "gemini-pro"
        assert kwargs["contents"] == "User prompt"

        # THE IMPORTANT CHECK: Verify config is GenerateContentConfig
        config_arg = kwargs["config"]
        assert isinstance(config_arg, MockGenerateContentConfig)
        assert config_arg.kwargs["system_instruction"] == "System prompt"
        assert config_arg.kwargs["temperature"] == 0.5


class TestOpenAICompatibleProviderGemini:
    def test_calculate_usage_uses_count_tokens_config_for_gemini(
        self, mock_google_modules
    ):
        """Verify that calculate_usage uses CountTokensConfig for gemini models via compatible provider."""
        mock_genai_mod, mock_client = mock_google_modules

        mock_response = MagicMock()
        mock_response.total_tokens = 150
        mock_client.models.count_tokens.return_value = mock_response

        # We need to set GOOGLE_API_KEY environment variable for this to trigger
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "fake-google-key"}):
            provider = OpenAICompatibleProvider(
                model="gemini/gemini-1.5-pro",  # Contains 'gemini'
                host="https://litellm.example.com",
                api_key="fake-key",
            )

            # Execute
            result = provider.calculate_usage("System prompt", "User prompt")

            # Verify
            assert result["token_count"] == 150

            # Check call arguments
            args, kwargs = mock_client.models.count_tokens.call_args
            assert kwargs["model"] == "models/gemini-1.5-pro"

            # Verify contents has both prompts
            assert kwargs["contents"] == ["System prompt", "User prompt"]

            # Verify no config is passed for system instruction
            assert "config" not in kwargs
