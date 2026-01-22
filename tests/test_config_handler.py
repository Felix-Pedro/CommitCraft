from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from commitcraft.config_handler import (
    validate_url,
    fetch_models,
    configure_provider,
    interactive_config,
)


class TestConfigHandler:
    # --- validate_url ---
    def test_validate_url(self):
        assert validate_url("http://localhost:11434") is True
        assert validate_url("https://api.openai.com") is True
        assert validate_url("ollama_cloud") is True
        assert validate_url("invalid-url") is False
        assert validate_url("") is False

    # --- fetch_models ---

    def test_fetch_models_ollama(self):
        # Patch global os.getenv since module doesn't import it at top level
        with patch("os.getenv") as mock_getenv:
            mock_getenv.return_value = None  # Default return None for OLLAMA_HOST etc.

            with patch("ollama.Client") as MockClient:
                mock_instance = MagicMock()
                MockClient.return_value = mock_instance
                mock_instance.list.return_value = {
                    "models": [{"name": "llama3"}, {"name": "mistral"}]
                }

                models = fetch_models("ollama", host="http://localhost")
                assert models == ["llama3", "mistral"]

    def test_fetch_models_openai(self):
        with patch("openai.OpenAI") as MockOpenAI:
            mock_client = MagicMock()
            MockOpenAI.return_value = mock_client
            mock_model = MagicMock()
            mock_model.id = "gpt-4"
            mock_client.models.list.return_value = [mock_model]

            models = fetch_models("openai", api_key="sk-test")
            assert models == ["gpt-4"]

    def test_fetch_models_anthropic(self):
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": [{"id": "claude-3-opus"}, {"id": "claude-3-sonnet"}]
            }
            mock_get.return_value = mock_response

            models = fetch_models("anthropic", api_key="sk-ant-test")
            assert models == ["claude-3-opus", "claude-3-sonnet"]

    # --- configure_provider ---

    @patch("typer.prompt")
    @patch("typer.confirm")
    @patch("commitcraft.config_handler.fetch_models")
    def test_configure_provider_flow(self, mock_fetch, mock_confirm, mock_prompt):
        # Scenario: Configure a new Ollama provider
        # Prompts:
        # 1. Provider Type (if not provided) -> "ollama"
        # 2. Ollama Host URL -> "http://localhost:11434"
        # 3. Model Name -> "llama3"

        mock_prompt.side_effect = [
            "ollama",
            "http://localhost:11434",
            "llama3",
        ]
        # Confirm: List available models? -> False
        mock_confirm.return_value = False

        config, key_info, env_var = configure_provider()

        assert config["provider"] == "ollama"
        assert config["host"] == "http://localhost:11434"
        assert config["model"] == "llama3"

    # --- interactive_config ---

    @patch("typer.prompt")
    @patch("typer.confirm")
    @patch("commitcraft.config_handler.load_existing_config")
    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_interactive_config_new_project(
        self, mock_file, mock_mkdir, mock_load, mock_confirm, mock_prompt
    ):
        # Scenario: New project, no existing config
        mock_load.return_value = ({}, None)

        # PROMPT SEQUENCE:
        # 1. Scope -> "project"
        # 2. Format -> "toml"
        # 3. Project Name -> "MyProject"
        # 4. Project Language -> "Python"
        # 5. Project Description -> "Test"
        # 6. Commit Guidelines -> "default"
        # 7. (Configure Main Provider) Provider -> "ollama"
        # 8. (Configure Main Provider) Host -> "http://localhost:11434"
        # 9. (Configure Main Provider) Model -> "llama3"
        # 10. (Emoji) Convention -> "simple" (Wait, only if emojis enabled)

        mock_prompt.side_effect = [
            "project",
            "toml",
            "MyProject",
            "Python",
            "Test",
            "default",
            # configure_provider
            "ollama",
            "http://localhost:11434",
            "llama3",
            # Emoji settings (only if confirmed) -> Let's say NO to emojis to keep it simple
        ]

        # CONFIRM SEQUENCE:
        # 1. Configure project-specific model settings? (Default True) -> True
        # 2. (Inside configure_provider) List available models? -> False
        # 3. Do you want to add/configure additional providers? -> False
        # 4. Enable Emojis? -> False
        # 5. Generate .ignore file? -> False
        # Add extra Falses just in case logic branches differently
        mock_confirm.side_effect = [True, False, False, False, False, False, False]
        with patch("pathlib.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/tmp/test")
            interactive_config()

        # Check if file was written
        assert mock_file.call_count >= 1
        handle = mock_file()
        content = "".join(call.args[0] for call in handle.write.call_args_list)
        assert "MyProject" in content
