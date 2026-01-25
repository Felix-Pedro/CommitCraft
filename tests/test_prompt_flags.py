"""
Tests for CLI flags and config settings that alter the prompt.

This test suite verifies that various flags and configuration options properly
modify the system prompt sent to the LLM. We use debug_prompt=True to inspect
the generated prompts without making actual API calls.
"""

import pytest
from commitcraft import (
    CommitCraftInput,
    EmojiConfig,
    EmojiSteps,
    LModel,
    Provider,
    commit_craft,
)
from commitcraft.defaults import default


# Fixtures


@pytest.fixture
def simple_diff():
    """A minimal diff for testing."""
    return """diff --git a/test.py b/test.py
new file mode 100644
index 0000000..d995a63
--- /dev/null
+++ b/test.py
@@ -0,0 +1 @@
+def hello(): pass
"""


@pytest.fixture
def default_model():
    """Default model configuration."""
    return LModel(provider=Provider.ollama, model="qwen3")


@pytest.fixture
def default_context():
    """Default project context."""
    return {
        "project_name": "TestProject",
        "project_language": "Python",
        "project_description": "A test project",
        "commit_guidelines": default["commit_guidelines"],
    }


# Emoji Flag Tests


def test_emoji_enabled_single_simple(simple_diff, default_model, default_context):
    """Test that emoji_steps='single' with 'simple' convention includes emoji guidelines."""
    inp = CommitCraftInput(diff=simple_diff)
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.single, emoji_convention="simple")

    prompt = commit_craft(
        inp, default_model, default_context, emoji_config, debug_prompt=True
    )

    # Should include GitMoji convention header
    assert "For the title of your message use the GitMoji Convention" in prompt
    # Should include some simple emojis
    assert "✨ ; Introduce new features" in prompt
    assert "🐛 ; Fix a bug" in prompt
    # Should NOT include the no-emoji instruction
    assert "Do NOT include any emojis" not in prompt


def test_emoji_enabled_single_full(simple_diff, default_model, default_context):
    """Test that emoji_steps='single' with 'full' convention includes full emoji set."""
    inp = CommitCraftInput(diff=simple_diff)
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.single, emoji_convention="full")

    prompt = commit_craft(
        inp, default_model, default_context, emoji_config, debug_prompt=True
    )

    # Should include GitMoji convention header
    assert "For the title of your message use the GitMoji Convention" in prompt
    # Should include emojis from the full set
    assert "🎨 ; Improve structure / format of the code" in prompt
    assert "🚀 ; Deploy stuff" in prompt
    # Should NOT include the no-emoji instruction
    assert "Do NOT include any emojis" not in prompt


def test_emoji_disabled_false(simple_diff, default_model, default_context):
    """Test that emoji_steps=False adds explicit no-emoji instruction."""
    inp = CommitCraftInput(diff=simple_diff)
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false, emoji_convention="simple")

    prompt = commit_craft(
        inp, default_model, default_context, emoji_config, debug_prompt=True
    )

    # Should NOT include emoji guidelines
    assert "For the title of your message use the GitMoji Convention" not in prompt
    assert "✨ ; Introduce new features" not in prompt
    # Should include explicit no-emoji instruction
    assert "IMPORTANT: Do NOT include any emojis in the commit message" in prompt
    assert "Use plain text only" in prompt


def test_emoji_custom_convention(simple_diff, default_model, default_context):
    """Test that custom emoji convention text is included."""
    inp = CommitCraftInput(diff=simple_diff)
    custom_emoji_text = "Use custom emoji format: [TYPE] message"
    emoji_config = EmojiConfig(
        emoji_steps=EmojiSteps.single, emoji_convention=custom_emoji_text
    )

    prompt = commit_craft(
        inp, default_model, default_context, emoji_config, debug_prompt=True
    )

    # Should include custom emoji text
    assert custom_emoji_text in prompt
    # Should NOT include standard emoji guidelines
    assert "For the title of your message use the GitMoji Convention" not in prompt


# Commit Clues Tests


def test_clue_bug_boolean(simple_diff, default_model, default_context):
    """Test that bug=True adds bug clue text to prompt."""
    inp = CommitCraftInput(diff=simple_diff, bug=True)
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    prompt = commit_craft(
        inp, default_model, default_context, emoji_config, debug_prompt=True
    )

    # Should include bug clue
    assert "This commit focus on fixing a bug" in prompt
    # Should show "Clues:" section
    assert "Clues:" in prompt


def test_clue_bug_description(simple_diff, default_model, default_context):
    """Test that bug='description' adds bug clue with description."""
    inp = CommitCraftInput(diff=simple_diff, bug="Fixed null pointer exception")
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    prompt = commit_craft(
        inp, default_model, default_context, emoji_config, debug_prompt=True
    )

    # Should include bug clue with description
    assert "This commit focus on fixing a bug" in prompt
    assert "Fixed null pointer exception" in prompt


def test_clue_feat_boolean(simple_diff, default_model, default_context):
    """Test that feat=True adds feature clue text to prompt."""
    inp = CommitCraftInput(diff=simple_diff, feat=True)
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    prompt = commit_craft(
        inp, default_model, default_context, emoji_config, debug_prompt=True
    )

    # Should include feature clue
    assert "This commit focus on a new feature" in prompt


def test_clue_feat_description(simple_diff, default_model, default_context):
    """Test that feat='description' adds feature clue with description."""
    inp = CommitCraftInput(diff=simple_diff, feat="Added dark mode")
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    prompt = commit_craft(
        inp, default_model, default_context, emoji_config, debug_prompt=True
    )

    # Should include feature clue with description
    assert "This commit focus on a new feature" in prompt
    assert "Added dark mode" in prompt


def test_clue_docs_boolean(simple_diff, default_model, default_context):
    """Test that docs=True adds docs clue text to prompt."""
    inp = CommitCraftInput(diff=simple_diff, docs=True)
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    prompt = commit_craft(
        inp, default_model, default_context, emoji_config, debug_prompt=True
    )

    # Should include docs clue
    assert "This commit focus on docs" in prompt


def test_clue_refact_boolean(simple_diff, default_model, default_context):
    """Test that refact=True adds refactoring clue text to prompt."""
    inp = CommitCraftInput(diff=simple_diff, refact=True)
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    prompt = commit_craft(
        inp, default_model, default_context, emoji_config, debug_prompt=True
    )

    # Should include refactoring clue
    assert "This commit focus on refactoring" in prompt


def test_clue_custom(simple_diff, default_model, default_context):
    """Test that custom_clue adds custom text to prompt."""
    inp = CommitCraftInput(diff=simple_diff, custom_clue="This is a security update")
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    prompt = commit_craft(
        inp, default_model, default_context, emoji_config, debug_prompt=True
    )

    # Should include custom clue
    assert "This is a security update" in prompt


def test_multiple_clues(simple_diff, default_model, default_context):
    """Test that multiple clues are all included in the prompt."""
    inp = CommitCraftInput(
        diff=simple_diff,
        bug="Fixed memory leak",
        docs="Updated API documentation",
    )
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    prompt = commit_craft(
        inp, default_model, default_context, emoji_config, debug_prompt=True
    )

    # Should include both clues
    assert "This commit focus on fixing a bug" in prompt
    assert "Fixed memory leak" in prompt
    assert "This commit focus on docs" in prompt
    assert "Updated API documentation" in prompt


# Context Tests


def test_context_project_name(simple_diff, default_model):
    """Test that project_name appears in the system prompt."""
    inp = CommitCraftInput(diff=simple_diff)
    context = {"project_name": "MyAwesomeProject"}
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    prompt = commit_craft(inp, default_model, context, emoji_config, debug_prompt=True)

    # Should include project name
    assert "MyAwesomeProject" in prompt


def test_context_project_language(simple_diff, default_model):
    """Test that project_language appears in the system prompt."""
    inp = CommitCraftInput(diff=simple_diff)
    context = {"project_language": "Rust"}
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    prompt = commit_craft(inp, default_model, context, emoji_config, debug_prompt=True)

    # Should include project language
    assert "Rust" in prompt


def test_context_project_description(simple_diff, default_model):
    """Test that project_description appears in the system prompt."""
    inp = CommitCraftInput(diff=simple_diff)
    context = {"project_description": "A high-performance web server"}
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    prompt = commit_craft(inp, default_model, context, emoji_config, debug_prompt=True)

    # Should include project description
    assert "A high-performance web server" in prompt


def test_context_commit_guidelines(simple_diff, default_model):
    """Test that custom commit_guidelines appear in the system prompt."""
    inp = CommitCraftInput(diff=simple_diff)
    custom_guidelines = "Always use present tense. Maximum 50 characters."
    context = {"commit_guidelines": custom_guidelines}
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    prompt = commit_craft(inp, default_model, context, emoji_config, debug_prompt=True)

    # Should include custom guidelines
    assert custom_guidelines in prompt


# Combined Flag Tests


def test_combined_emoji_and_bug_clue(simple_diff, default_model, default_context):
    """Test emoji guidelines and bug clue together."""
    inp = CommitCraftInput(diff=simple_diff, bug="Fixed race condition")
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.single, emoji_convention="simple")

    prompt = commit_craft(
        inp, default_model, default_context, emoji_config, debug_prompt=True
    )

    # Should include emoji guidelines
    assert "For the title of your message use the GitMoji Convention" in prompt
    assert "🐛 ; Fix a bug" in prompt
    # Should include bug clue
    assert "This commit focus on fixing a bug" in prompt
    assert "Fixed race condition" in prompt
    # Should NOT include no-emoji instruction
    assert "Do NOT include any emojis" not in prompt


def test_combined_no_emoji_and_feat_clue(simple_diff, default_model, default_context):
    """Test no-emoji instruction and feature clue together."""
    inp = CommitCraftInput(diff=simple_diff, feat="Added user authentication")
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    prompt = commit_craft(
        inp, default_model, default_context, emoji_config, debug_prompt=True
    )

    # Should include no-emoji instruction
    assert "IMPORTANT: Do NOT include any emojis" in prompt
    # Should include feature clue
    assert "This commit focus on a new feature" in prompt
    assert "Added user authentication" in prompt
    # Should NOT include emoji guidelines
    assert "For the title of your message use the GitMoji Convention" not in prompt


def test_combined_all_clues_with_emoji(simple_diff, default_model, default_context):
    """Test all clues combined with emoji enabled."""
    inp = CommitCraftInput(
        diff=simple_diff,
        bug="Fixed crash",
        feat="Added logging",
        docs="Updated README",
        refact="Simplified code",
        custom_clue="Breaking change",
    )
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.single, emoji_convention="full")

    prompt = commit_craft(
        inp, default_model, default_context, emoji_config, debug_prompt=True
    )

    # Should include all clues
    assert "Fixed crash" in prompt
    assert "Added logging" in prompt
    assert "Updated README" in prompt
    assert "Simplified code" in prompt
    assert "Breaking change" in prompt
    # Should include emoji guidelines (full set)
    assert "For the title of your message use the GitMoji Convention" in prompt
    assert "🎨 ; Improve structure / format of the code" in prompt


def test_combined_custom_context_and_no_emoji(simple_diff, default_model):
    """Test custom context with no-emoji setting."""
    inp = CommitCraftInput(diff=simple_diff)
    context = {
        "project_name": "CommitCraft",
        "project_language": "Python",
        "project_description": "AI-powered commit message generator",
        "commit_guidelines": "Keep it short. Use conventional commits.",
    }
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    prompt = commit_craft(inp, default_model, context, emoji_config, debug_prompt=True)

    # Should include all context fields
    assert "CommitCraft" in prompt
    assert "Python" in prompt
    assert "AI-powered commit message generator" in prompt
    assert "Keep it short. Use conventional commits." in prompt
    # Should include no-emoji instruction
    assert "IMPORTANT: Do NOT include any emojis" in prompt
    # Should NOT include emoji guidelines
    assert "For the title of your message use the GitMoji Convention" not in prompt


# Diff Content Tests


def test_diff_content_in_prompt(simple_diff, default_model, default_context):
    """Test that the diff content appears in the user prompt section."""
    inp = CommitCraftInput(diff=simple_diff)
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    prompt = commit_craft(
        inp, default_model, default_context, emoji_config, debug_prompt=True
    )

    # Should have prompt sections
    assert "system_prompt:" in prompt
    assert "prompt:" in prompt
    # Should include diff markers
    assert "Beginning of the diff" in prompt
    assert "End of the diff" in prompt
    # Should include actual diff content
    assert "def hello(): pass" in prompt
    assert "diff --git a/test.py b/test.py" in prompt


# System Prompt Structure Tests


def test_system_prompt_has_proposure_section(
    simple_diff, default_model, default_context
):
    """Test that system prompt includes the 'Proposure' section."""
    inp = CommitCraftInput(diff=simple_diff)
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    prompt = commit_craft(
        inp, default_model, default_context, emoji_config, debug_prompt=True
    )

    # Should have the purpose header
    assert "# Proposure" in prompt or "You are a commit message helper" in prompt


def test_system_prompt_has_guidelines(simple_diff, default_model, default_context):
    """Test that system prompt includes commit guidelines."""
    inp = CommitCraftInput(diff=simple_diff)
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    prompt = commit_craft(
        inp, default_model, default_context, emoji_config, debug_prompt=True
    )

    # Should include default guidelines
    assert "Be concise and clear" in prompt
    assert "Use action verbs" in prompt
    assert "Do not return any explanation other" in prompt


# Edge Cases


def test_empty_context(simple_diff, default_model):
    """Test that empty context doesn't break prompt generation."""
    inp = CommitCraftInput(diff=simple_diff)
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    prompt = commit_craft(inp, default_model, {}, emoji_config, debug_prompt=True)

    # Should still generate a valid prompt
    assert "system_prompt:" in prompt
    assert "prompt:" in prompt


def test_no_emoji_config(simple_diff, default_model, default_context):
    """Test that None emoji config doesn't add emoji guidelines or no-emoji instruction."""
    inp = CommitCraftInput(diff=simple_diff)

    prompt = commit_craft(inp, default_model, default_context, None, debug_prompt=True)

    # Should NOT include emoji guidelines
    assert "For the title of your message use the GitMoji Convention" not in prompt
    # Should NOT include no-emoji instruction
    assert "Do NOT include any emojis" not in prompt


def test_custom_system_prompt(simple_diff, default_context):
    """Test that custom system_prompt is used instead of default."""
    inp = CommitCraftInput(diff=simple_diff)
    custom_prompt = "You are a strict commit message enforcer. {{ project_name }}"
    model = LModel(provider=Provider.ollama, model="qwen3", system_prompt=custom_prompt)
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    prompt = commit_craft(inp, model, default_context, emoji_config, debug_prompt=True)

    # Should include custom prompt
    assert "You are a strict commit message enforcer" in prompt
    # Should have rendered Jinja2 template with context
    assert "TestProject" in prompt


# No Clues Test


def test_no_clues_no_clues_section(simple_diff, default_model, default_context):
    """Test that when no clues are provided, the Clues section doesn't appear."""
    inp = CommitCraftInput(diff=simple_diff)
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    prompt = commit_craft(
        inp, default_model, default_context, emoji_config, debug_prompt=True
    )

    # Should NOT have Clues section when no clues provided
    assert "Clues:" not in prompt


# Dry Run and Debug Prompt Combined Tests


def test_dry_run_only(simple_diff, default_model, default_context):
    """Test that dry_run=True without debug_prompt returns usage statistics."""
    inp = CommitCraftInput(diff=simple_diff)
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    result = commit_craft(
        inp,
        default_model,
        default_context,
        emoji_config,
        debug_prompt=False,
        dry_run=True,
    )

    # Should return a dictionary with token statistics
    assert isinstance(result, dict)
    assert "token_count" in result
    assert "system_prompt_tokens" in result
    assert "user_prompt_tokens" in result
    assert "model" in result
    assert "provider" in result

    # Should NOT include prompts when debug_prompt is False
    assert "system_prompt" not in result
    assert "user_prompt" not in result


def test_debug_prompt_only(simple_diff, default_model, default_context):
    """Test that debug_prompt=True without dry_run returns formatted prompt string."""
    inp = CommitCraftInput(diff=simple_diff)
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    result = commit_craft(
        inp,
        default_model,
        default_context,
        emoji_config,
        debug_prompt=True,
        dry_run=False,
    )

    # Should return a formatted string
    assert isinstance(result, str)
    assert "system_prompt:" in result
    assert "prompt:" in result
    assert "You are a commit message helper" in result
    assert "def hello(): pass" in result


def test_dry_run_and_debug_prompt_combined(simple_diff, default_model, default_context):
    """Test that dry_run=True AND debug_prompt=True returns both stats and prompts."""
    inp = CommitCraftInput(diff=simple_diff)
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    result = commit_craft(
        inp,
        default_model,
        default_context,
        emoji_config,
        debug_prompt=True,
        dry_run=True,
    )

    # Should return a dictionary with both statistics AND prompts
    assert isinstance(result, dict)

    # Should include token statistics
    assert "token_count" in result
    assert "system_prompt_tokens" in result
    assert "user_prompt_tokens" in result
    assert "model" in result
    assert "provider" in result

    # Should ALSO include full prompts
    assert "system_prompt" in result
    assert "user_prompt" in result

    # Verify prompt content
    assert "You are a commit message helper" in result["system_prompt"]
    assert "def hello(): pass" in result["user_prompt"]
    assert "Beginning of the diff" in result["user_prompt"]


def test_dry_run_debug_prompt_with_emoji_enabled(
    simple_diff, default_model, default_context
):
    """Test dry_run + debug_prompt includes emoji guidelines in system prompt."""
    inp = CommitCraftInput(diff=simple_diff)
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.single, emoji_convention="simple")

    result = commit_craft(
        inp,
        default_model,
        default_context,
        emoji_config,
        debug_prompt=True,
        dry_run=True,
    )

    # Should be a dictionary with both stats and prompts
    assert isinstance(result, dict)
    assert "system_prompt" in result
    assert "user_prompt" in result

    # System prompt should include emoji guidelines
    assert (
        "For the title of your message use the GitMoji Convention"
        in result["system_prompt"]
    )
    assert "✨ ; Introduce new features" in result["system_prompt"]

    # Token counts should reflect the added emoji guidelines
    assert result["token_count"] > 0
    assert result["system_prompt_tokens"] > 0


def test_dry_run_debug_prompt_with_no_emoji(
    simple_diff, default_model, default_context
):
    """Test dry_run + debug_prompt includes no-emoji instruction when emoji disabled."""
    inp = CommitCraftInput(diff=simple_diff)
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    result = commit_craft(
        inp,
        default_model,
        default_context,
        emoji_config,
        debug_prompt=True,
        dry_run=True,
    )

    # Should be a dictionary
    assert isinstance(result, dict)
    assert "system_prompt" in result

    # System prompt should include no-emoji instruction
    assert "IMPORTANT: Do NOT include any emojis" in result["system_prompt"]
    assert "Use plain text only" in result["system_prompt"]

    # Should NOT include emoji guidelines
    assert (
        "For the title of your message use the GitMoji Convention"
        not in result["system_prompt"]
    )


def test_dry_run_debug_prompt_with_clues(simple_diff, default_model, default_context):
    """Test dry_run + debug_prompt includes clues in the prompt."""
    inp = CommitCraftInput(
        diff=simple_diff, bug="Fixed memory leak", feat="Added caching"
    )
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    result = commit_craft(
        inp,
        default_model,
        default_context,
        emoji_config,
        debug_prompt=True,
        dry_run=True,
    )

    # Should include both statistics and prompts
    assert isinstance(result, dict)
    assert "user_prompt" in result

    # User prompt should include clues
    assert "Fixed memory leak" in result["user_prompt"]
    assert "Added caching" in result["user_prompt"]
    assert "Clues:" in result["user_prompt"]


def test_dry_run_debug_prompt_token_count_accuracy(
    simple_diff, default_model, default_context
):
    """Test that token counts are accurate when using dry_run + debug_prompt."""
    inp = CommitCraftInput(diff=simple_diff)
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    result = commit_craft(
        inp,
        default_model,
        default_context,
        emoji_config,
        debug_prompt=True,
        dry_run=True,
    )

    # Verify token count relationship
    assert isinstance(result, dict)
    assert result["token_count"] > 0
    assert result["system_prompt_tokens"] > 0
    assert result["user_prompt_tokens"] > 0

    # Total should be sum of system + user tokens
    assert (
        result["token_count"]
        == result["system_prompt_tokens"] + result["user_prompt_tokens"]
    )


def test_dry_run_debug_prompt_returns_dict_with_prompts(
    simple_diff, default_model, default_context
):
    """Test that combining dry_run and debug_prompt returns a dict (not a string)."""
    inp = CommitCraftInput(diff=simple_diff)
    emoji_config = EmojiConfig(emoji_steps=EmojiSteps.false)

    # When using ONLY debug_prompt, it returns a string
    result_debug_only = commit_craft(
        inp,
        default_model,
        default_context,
        emoji_config,
        debug_prompt=True,
        dry_run=False,
    )
    assert isinstance(result_debug_only, str)

    # When using BOTH dry_run AND debug_prompt, it returns a dict
    result_combined = commit_craft(
        inp,
        default_model,
        default_context,
        emoji_config,
        debug_prompt=True,
        dry_run=True,
    )
    assert isinstance(result_combined, dict)
    assert "system_prompt" in result_combined
    assert "user_prompt" in result_combined
    assert "token_count" in result_combined
