import sys
from commitcraft.config_handler import validate_url, fetch_models
from unittest.mock import patch, MagicMock


def test_validate_url_valid():
    assert validate_url("http://localhost:11434") is True
    assert validate_url("https://api.openai.com") is True
    assert validate_url("ollama_cloud") is True


def test_validate_url_invalid():
    assert validate_url("not_a_url") is False
    # urlparse accepts scheme+netloc, validation function checks scheme and netloc presence
    assert validate_url("http://") is False  # no netloc


def test_fetch_models_ollama():
    # Mock ollama module
    mock_ollama = MagicMock()
    mock_client = mock_ollama.Client.return_value
    mock_client.list.return_value = {"models": [{"name": "model1"}, {"name": "model2"}]}

    with patch.dict(sys.modules, {"ollama": mock_ollama}):
        models = fetch_models("ollama", host="http://localhost:11434")

    assert models == ["model1", "model2"]
    mock_ollama.Client.assert_called_with(host="http://localhost:11434")


def test_fetch_models_openai():
    # Mock openai module
    mock_openai = MagicMock()
    mock_client = mock_openai.OpenAI.return_value
    mock_model1 = MagicMock()
    mock_model1.id = "gpt-4"
    mock_model2 = MagicMock()
    mock_model2.id = "gpt-3.5-turbo"
    mock_client.models.list.return_value = [mock_model1, mock_model2]

    with patch.dict(sys.modules, {"openai": mock_openai}):
        models = fetch_models("openai", api_key="fake-key")

    assert models == ["gpt-4", "gpt-3.5-turbo"]
    mock_openai.OpenAI.assert_called_with(api_key="fake-key")
