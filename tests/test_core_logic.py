import pytest
from unittest.mock import MagicMock, patch
import sys
from commitcraft.CommitCraft import (
    clue_parser, 
    CommitCraftInput, 
    LModel, 
    Provider, 
    commit_craft,
    EmojiConfig
)

from pydantic import ValidationError

# --- Clue Parser Tests ---

def test_clue_parser_booleans():
    inp = CommitCraftInput(diff="diff", bug=True, feat=False)
    parsed = clue_parser(inp)
    assert parsed['bug'] == 'This commit focus on fixing a bug'
    assert 'feat' not in parsed

def test_clue_parser_strings():
    inp = CommitCraftInput(diff="diff", bug="Fix typo")
    parsed = clue_parser(inp)
    # Code does not add space after colon for string clues
    assert parsed['bug'] == 'This commit focus on fixing a bug: Fix typo'

def test_clue_parser_custom():
    inp = CommitCraftInput(diff="diff", custom_clue="My clue")
    parsed = clue_parser(inp)
    assert parsed['custom_clue'] == "My clue"

# --- LModel Validator Tests ---

def test_lmodel_defaults():
    # Default provider is ollama, should default model to qwen3
    model = LModel()
    assert model.provider == Provider.ollama
    assert model.model == "qwen3"

def test_lmodel_openai_default():
    model = LModel(provider=Provider.openai)
    assert model.model == "gpt-3.5-turbo"

def test_lmodel_openai_compatible_missing_model():
    with pytest.raises(ValidationError) as excinfo:
        LModel(provider=Provider.openai_compatible, host="http://localhost:1234")
    assert "The model cannot be None" in str(excinfo.value)

def test_lmodel_openai_compatible_missing_host():
    with pytest.raises(ValidationError) as excinfo:
        LModel(provider=Provider.openai_compatible, model="my-model")
    assert "The 'host' field is required" in str(excinfo.value)

def test_lmodel_openai_compatible_valid():
    model = LModel(
        provider=Provider.openai_compatible, 
        model="my-model", 
        host="http://localhost:1234"
    )
    assert model.model == "my-model"
    assert str(model.host) == "http://localhost:1234/"

# --- Commit Craft Logic Tests ---

def test_commit_craft_debug_prompt():
    inp = CommitCraftInput(diff="diff")
    model = LModel(provider=Provider.ollama, model="qwen3")
    res = commit_craft(inp, model, debug_prompt=True)
    assert "system_prompt:" in res
    assert "prompt:" in res
    assert "diff" in res

def test_commit_craft_ollama_cloud():
    inp = CommitCraftInput(diff="diff")
    model = LModel(
        provider=Provider.ollama_cloud, 
        model="qwen3-coder:480b-cloud",
        api_key="test-key"
    )
    
    mock_ollama = MagicMock()
    mock_client = mock_ollama.Client.return_value
    mock_client.chat.return_value = {"message": {"content": "Commit message"}}
    
    with patch.dict(sys.modules, {'ollama': mock_ollama}):
        res = commit_craft(inp, model)
    
    assert res == "Commit message"
    # Check client init with correct host and headers
    mock_ollama.Client.assert_called_with(
        host="https://ollama.com", 
        headers={"Authorization": "Bearer test-key"}
    )
    # Check chat called
    mock_client.chat.assert_called()

def test_commit_craft_openai():
    inp = CommitCraftInput(diff="diff")
    model = LModel(
        provider=Provider.openai, 
        model="gpt-4", 
        api_key="sk-test"
    )
    
    mock_openai_pkg = MagicMock()
    mock_client = mock_openai_pkg.OpenAI.return_value
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="GPT Commit"))]
    mock_client.chat.completions.create.return_value = mock_response
    
    with patch.dict(sys.modules, {'openai': mock_openai_pkg}):
        res = commit_craft(inp, model)
        
    assert res == "GPT Commit"
    mock_openai_pkg.OpenAI.assert_called_with(api_key="sk-test")

def test_commit_craft_groq():
    inp = CommitCraftInput(diff="diff")
    model = LModel(
        provider=Provider.groq,
        model="llama3",
        api_key="gsk-test"
    )
    
    mock_groq_pkg = MagicMock()
    mock_client = mock_groq_pkg.Groq.return_value
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Groq Commit"))]
    mock_client.chat.completions.create.return_value = mock_response
    
    with patch.dict(sys.modules, {'groq': mock_groq_pkg}):
        res = commit_craft(inp, model)
        
    assert res == "Groq Commit"
    mock_groq_pkg.Groq.assert_called_with(api_key="gsk-test")

def test_commit_craft_emoji_handling():
    inp = CommitCraftInput(diff="diff")
    model = LModel(provider=Provider.ollama)
    emoji_config = EmojiConfig(emoji_steps="single", emoji_convention="simple")
    
    # We debug prompt to check if emoji guidelines are appended
    res = commit_craft(inp, model, emoji=emoji_config, debug_prompt=True)
    
    # defaults.py has emoji guidelines
    from commitcraft.defaults import default
    simple_guide = default['emoji_guidelines']['simple']
    assert simple_guide in res
