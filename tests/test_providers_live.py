import os

import pytest

from commitcraft.providers import (
    AnthropicProvider,
    GoogleProvider,
    GroqProvider,
    OllamaProvider,
    OpenAIProvider,
)

# Common test data
SYSTEM_PROMPT = "You are a test assistant. Reply with 'OK'."
USER_PROMPT = "Test."


@pytest.mark.live
class TestProvidersLive:
    """
    Integration tests that make real API calls.
    Run with: pytest -m live
    """

    @pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set"
    )
    def test_openai_live(self):
        provider = OpenAIProvider(
            model="gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
            options={"max_tokens": 10, "temperature": 0},
        )
        try:
            response = provider.generate(SYSTEM_PROMPT, USER_PROMPT)
            assert len(response) > 0
            print(f"\nOpenAI Response: {response}")
        except Exception as e:
            if "quota" in str(e).lower():
                pytest.skip("OpenAI quota exceeded")
            raise e

    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY not set"
    )
    def test_anthropic_live(self):
        provider = AnthropicProvider(
            model="claude-3-haiku-20240307",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            options={"max_tokens": 10, "temperature": 0},
        )
        try:
            response = provider.generate(SYSTEM_PROMPT, USER_PROMPT)
            assert len(response) > 0
            print(f"\nAnthropic Response: {response}")
        except Exception as e:
            if "credit" in str(e).lower() or "balance" in str(e).lower():
                pytest.skip("Anthropic insufficient credits")
            raise e

    @pytest.mark.skipif(not os.getenv("GROQ_API_KEY"), reason="GROQ_API_KEY not set")
    def test_groq_live(self):
        provider = GroqProvider(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            options={"max_tokens": 10, "temperature": 0},
        )
        try:
            response = provider.generate(SYSTEM_PROMPT, USER_PROMPT)
            assert len(response) > 0
            print(f"\nGroq Response: {response}")
        except Exception as e:
            if "decommissioned" in str(e).lower() or "limit" in str(e).lower():
                pytest.skip(f"Groq error: {e}")
            raise e

    @pytest.mark.skipif(
        not os.getenv("GOOGLE_API_KEY"), reason="GOOGLE_API_KEY not set"
    )
    def test_google_live(self):
        provider = GoogleProvider(
            model="gemini-2.5-flash-lite",
            api_key=os.getenv("GOOGLE_API_KEY"),
            options={"max_tokens": 10, "temperature": 0},
        )
        try:
            response = provider.generate(SYSTEM_PROMPT, USER_PROMPT)
            assert len(response) > 0
            print(f"\nGoogle Response: {response}")
        except Exception as e:
            if "not found" in str(e).lower() or "404" in str(e):
                pytest.skip(f"Google model not found/available: {e}")
            raise e

    @pytest.mark.skipif(
        os.getenv("CI") == "true", reason="Skipping local Ollama test in CI"
    )
    def test_ollama_local_live(self):
        # Only run if OLLAMA_HOST is reachable or default localhost is up
        try:
            import requests

            host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
            requests.get(host, timeout=1)
        except Exception:
            pytest.skip("Ollama not running locally")

        model = os.getenv("OLLAMA_TEST_MODEL", "qwen3")

        provider = OllamaProvider(
            model=model,
            host=os.getenv("OLLAMA_HOST"),
            options={"num_ctx": 1024, "temperature": 0},
        )
        try:
            response = provider.generate(SYSTEM_PROMPT, USER_PROMPT)
            assert len(response) > 0
            print(f"\nOllama Response: {response}")
        except Exception as e:
            if "model" in str(e) and "not found" in str(e):
                pytest.skip(f"Ollama model '{model}' not found")
            else:
                raise e
