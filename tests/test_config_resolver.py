import os
import pytest
from unittest.mock import patch
from commitcraft.config_resolver import (
    resolve_named_provider,
    resolve_provider_config,
    apply_cli_overrides,
    resolve_model_configuration,
)
from commitcraft.CommitCraft import LModel


class TestConfigResolver:
    @pytest.fixture
    def mock_config(self):
        return {
            "models": {
                "provider": "ollama",
                "model": "llama3",
                "options": {"num_ctx": 4096},
            },
            "providers": {
                "remote_ollama": {
                    "provider": "ollama",
                    "host": "http://remote:11434",
                    "model": "qwen2",
                },
                "deepseek": {
                    "provider": "openai_compatible",
                    "host": "https://api.deepseek.com",
                    "model": "deepseek-coder",
                },
            },
        }

    # --- resolve_named_provider ---

    def test_resolve_named_provider_success(self, mock_config):
        model = resolve_named_provider("remote_ollama", mock_config["providers"])
        assert model.provider == "ollama"
        assert str(model.host) == "http://remote:11434/"
        assert model.model == "qwen2"

    def test_resolve_named_provider_missing(self, mock_config):
        with pytest.raises(KeyError, match="Provider profile 'unknown' not found"):
            resolve_named_provider("unknown", mock_config["providers"])

    def test_resolve_named_provider_api_key_env(self, mock_config):
        # Test implicit API key resolution from environment: DEEPSEEK_API_KEY
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test-key"}):
            model = resolve_named_provider("deepseek", mock_config["providers"])
            assert model.api_key == "sk-test-key"

    # --- resolve_provider_config ---

    def test_resolve_provider_config_named(self, mock_config):
        # Should resolve "remote_ollama" from [providers]
        model = resolve_provider_config("remote_ollama", mock_config)
        assert str(model.host) == "http://remote:11434/"

    def test_resolve_provider_config_standard_args(self, mock_config):
        model = resolve_provider_config("openai", mock_config)
        # It should return the DEFAULT model from config['models']
        assert model.provider == "ollama"  # Default in mock_config
        assert model.model == "llama3"

    def test_resolve_provider_config_default(self, mock_config):
        # No provider arg -> use default [models]
        model = resolve_provider_config(None, mock_config)
        assert model.provider == "ollama"
        assert model.options.num_ctx == 4096

    def test_resolve_provider_config_empty_config(self):
        # Empty config -> default LModel
        model = resolve_provider_config(None, {})
        assert model.provider == "ollama"  # Default in LModel definition

    # --- apply_cli_overrides ---

    def test_apply_cli_overrides(self):
        base = LModel(
            provider="ollama",
            model="llama3",
            options={"num_ctx": 4096, "temperature": 0.7},
        )
        cli_args = {
            "provider": "openai",  # Override
            "model": "gpt-4",  # Override
            "num_ctx": None,  # Keep
            "temperature": 0.1,  # Override
            "max_tokens": 100,  # New
            "host": None,
            "system_prompt": None,
        }

        result = apply_cli_overrides(base, cli_args)

        assert result.provider == "openai"
        assert result.model == "gpt-4"
        assert result.options.num_ctx == 4096
        assert result.options.temperature == 0.1
        assert result.options.max_tokens == 100

    def test_apply_cli_overrides_api_key_preserved(self):
        # API Key should strictly come from base (config/env), never CLI (security)
        base = LModel(provider="ollama", api_key="secret")

        # We need to fill all expected keys for the function
        full_args = {
            "provider": None,
            "model": None,
            "system_prompt": None,
            "host": None,
            "num_ctx": None,
            "temperature": None,
            "max_tokens": None,
        }

        result = apply_cli_overrides(base, full_args)
        assert result.api_key == "secret"

    # --- resolve_model_configuration (Integration) ---

    def test_resolve_model_configuration_integration(self, mock_config):
        # Scenario: User requests named profile 'remote_ollama'
        # This previously failed because 'remote_ollama' was passed as provider type
        model = resolve_model_configuration(
            provider="remote_ollama",
            model=None,
            system_prompt=None,
            host=None,
            num_ctx=None,
            temperature=None,
            max_tokens=None,
            config=mock_config,
        )

        assert model.provider == "ollama"  # From profile
        assert str(model.host) == "http://remote:11434/"
        assert model.model == "qwen2"

        # Scenario: User requests named profile but overrides model
        model2 = resolve_model_configuration(
            provider="remote_ollama",
            model="qwen2.5",
            system_prompt=None,
            host=None,
            num_ctx=None,
            temperature=None,
            max_tokens=None,
            config=mock_config,
        )
        assert model2.model == "qwen2.5"
