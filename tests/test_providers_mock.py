import pytest
from unittest.mock import MagicMock, patch
from commitcraft.providers import (
    OpenAIProvider,
    AnthropicProvider,
    GroqProvider,
    OllamaProvider,
    OllamaCloudProvider,
)


@pytest.fixture
def mock_openai_module():
    with patch("openai.OpenAI") as mock:
        yield mock


@pytest.fixture
def mock_anthropic_module():
    with patch("anthropic.Anthropic") as mock:
        yield mock


@pytest.fixture
def mock_groq_module():
    with patch("groq.Groq") as mock:
        yield mock


@pytest.fixture
def mock_ollama_module():
    with patch("ollama.Client") as mock:
        yield mock


class TestOpenAIProvider:
    def test_generate(self, mock_openai_module):
        # Setup mock
        mock_client = MagicMock()
        mock_openai_module.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Mocked commit message"
        mock_client.chat.completions.create.return_value = mock_response

        # Initialize provider
        provider = OpenAIProvider(
            model="gpt-4o", api_key="sk-test", options={"temperature": 0.7}
        )

        # Execute
        result = provider.generate("System prompt", "User prompt")

        # Verify
        assert result == "Mocked commit message"
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o"
        assert call_kwargs["messages"] == [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "User prompt"},
        ]
        assert call_kwargs["temperature"] == 0.7

    def test_generate_error(self, mock_openai_module):
        mock_client = MagicMock()
        mock_openai_module.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        provider = OpenAIProvider(model="gpt-4o", api_key="sk-test")

        with pytest.raises(Exception, match="OpenAI generation failed"):
            provider.generate("System", "User")


class TestAnthropicProvider:
    def test_generate(self, mock_anthropic_module):
        # Setup mock
        mock_client = MagicMock()
        mock_anthropic_module.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Mocked Claude response")]
        mock_client.messages.create.return_value = mock_response

        # Initialize provider
        provider = AnthropicProvider(
            model="claude-3-opus", api_key="sk-ant-test", options={"max_tokens": 500}
        )

        # Execute
        result = provider.generate("System prompt", "User prompt")

        # Verify
        assert result == "Mocked Claude response"
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-3-opus"
        assert call_kwargs["system"] == "System prompt"
        assert call_kwargs["max_tokens"] == 500

    def test_calculate_usage_native(self, mock_anthropic_module):
        # Setup mock
        mock_client = MagicMock()
        mock_anthropic_module.return_value = mock_client
        mock_response = MagicMock()
        mock_response.input_tokens = 42
        mock_client.messages.count_tokens.return_value = mock_response

        provider = AnthropicProvider(model="claude-3-sonnet", api_key="sk-ant-test")

        # Execute
        result = provider.calculate_usage("System", "User")

        # Verify - should be 84 since count_tokens is called twice (system + user)
        assert result["token_count"] == 84
        assert mock_client.messages.count_tokens.call_count == 2


class TestGroqProvider:
    def test_generate(self, mock_groq_module):
        # Setup mock
        mock_client = MagicMock()
        mock_groq_module.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Mocked Groq response"
        mock_client.chat.completions.create.return_value = mock_response

        # Initialize provider
        provider = GroqProvider(model="llama3-70b", api_key="gsk-test")

        # Execute
        result = provider.generate("System prompt", "User prompt")

        # Verify
        assert result == "Mocked Groq response"
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "llama3-70b"


class TestOllamaProvider:
    def test_generate_local(self, mock_ollama_module):
        # Setup mock
        mock_client = MagicMock()
        mock_ollama_module.return_value = mock_client
        mock_client.generate.return_value = {"response": "Mocked Ollama response"}

        # Initialize provider
        provider = OllamaProvider(
            model="llama3", options={"num_ctx": 4096}, host="http://localhost:11434"
        )

        # Execute
        result = provider.generate("System prompt", "User prompt")

        # Verify
        assert result == "Mocked Ollama response"
        mock_client.generate.assert_called_once()
        call_kwargs = mock_client.generate.call_args[1]
        assert call_kwargs["model"] == "llama3"
        assert call_kwargs["system"] == "System prompt"
        assert call_kwargs["prompt"] == "User prompt"
        assert call_kwargs["options"]["num_ctx"] == 4096

    def test_calculate_usage_tiktoken_fallback(self, mock_ollama_module):
        # Test calculation when tiktoken is available (mocking it via sys.modules isn't easy here,
        # so we rely on the provider's internal behavior or mock the _count_tokens method if needed.
        # But simpler: the provider falls back to char ratio if tiktoken fails.
        # Let's assume tiktoken works (default in dev env) or fails.
        # We can mock _count_tokens directly for stable testing.

        provider = OllamaProvider(model="llama3")
        with patch.object(provider, "_count_tokens", return_value=100):
            result = provider.calculate_usage("System", "User")

        # Should be 200 since _count_tokens is called twice (system + user), each returning 100
        assert result["token_count"] == 200
        assert "context_size" in result


class TestOllamaCloudProvider:
    def test_generate(self, mock_ollama_module):
        # Setup mock
        mock_client = MagicMock()
        mock_ollama_module.return_value = mock_client
        mock_client.chat.return_value = {
            "message": {"content": "Mocked Cloud response"}
        }

        # Initialize provider
        provider = OllamaCloudProvider(model="llama3", api_key="ollama-key")

        # Execute
        result = provider.generate("System prompt", "User prompt")

        # Verify
        assert result == "Mocked Cloud response"
        mock_client.chat.assert_called_once()
        call_kwargs = mock_client.chat.call_args[1]
        assert call_kwargs["messages"] == [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "User prompt"},
        ]
