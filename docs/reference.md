# API Reference

This page documents CommitCraft's Python API for use as a library in custom scripts and automation.

## Installation

```bash
pip install commitcraft

# Or with specific provider support
pip install commitcraft[all-providers]
```

## Quick Start

```python
from commitcraft import commit_craft, CommitCraftInput, LModel, get_diff

# Get your git diff
diff = get_diff()

# Create input
input_data = CommitCraftInput(diff=diff)

# Configure model
model = LModel(provider="ollama", model="qwen3")

# Generate commit message
message = commit_craft(input=input_data, models=model)
print(message)
```

---

## Core Functions

### `commit_craft()`

Main function that generates commit messages based on diffs and configuration.

**Signature:**
```python
def commit_craft(
    input: CommitCraftInput,
    models: LModel = LModel(),
    context: dict[str, str] = {},
    emoji: Optional[EmojiConfig] = None,
    debug_prompt: bool = False,
    dry_run: bool = False,
) -> str | dict
```

**Parameters:**

| Parameter | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `input` | `CommitCraftInput` | ✅ | Input containing diff and optional clues |
| `models` | `LModel` | ❌ | Model configuration (defaults to Ollama/qwen3) |
| `context` | `dict[str, str]` | ❌ | Context variables for prompt templates |
| `emoji` | `EmojiConfig \| None` | ❌ | Emoji configuration |
| `debug_prompt` | `bool` | ❌ | If True, returns prompt without calling AI |
| `dry_run` | `bool` | ❌ | If True, returns token usage statistics without generating message |

**Returns:** 
- `str` - Generated commit message (when `debug_prompt=False` and `dry_run=False`)
- `str` - Prompt text (when `debug_prompt=True`)
- `dict` - Token usage statistics (when `dry_run=True`)

**Example:**
```python
from commitcraft import commit_craft, CommitCraftInput, LModel, EmojiConfig, EmojiSteps

input_data = CommitCraftInput(
    diff="diff --git a/file.py ...",
    feat="Added user authentication",
)

model = LModel(
    provider="openai",
    model="gpt-4",
    options={"temperature": 0.7, "max_tokens": 500}
)

context = {
    "project_name": "MyApp",
    "project_language": "Python",
    "commit_guidelines": "Use conventional commits"
}

emoji_config = EmojiConfig(
    emoji_steps=EmojiSteps.single,
    emoji_convention="simple"
)

message = commit_craft(
    input=input_data,
    models=model,
    context=context,
    emoji=emoji_config
)

# Or get token usage without generating
usage_stats = commit_craft(
    input=input_data,
    models=model,
    context=context,
    emoji=emoji_config,
    dry_run=True
)
# Returns: {
#   'provider': 'openai',
#   'model': 'gpt-4',
#   'input_tokens': 1234,
#   'system_prompt_tokens': 156,
#   'total_tokens': 1390,
#   'host': 'https://api.openai.com'
# }
```

---

### `get_diff()`

Retrieves staged changes from git.

**Signature:**
```python
def get_diff() -> str
```

**Returns:** `str` - Output of `git diff --staged -M`

**Example:**
```python
from commitcraft import get_diff

diff = get_diff()
print(diff)
```

---

### `filter_diff()`

Filters diff output to exclude files matching ignore patterns.

**Signature:**
```python
def filter_diff(diff_output: str, ignored_patterns: List[str]) -> str
```

**Parameters:**

| Parameter | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `diff_output` | `str` | ✅ | Raw diff output |
| `ignored_patterns` | `List[str]` | ✅ | fnmatch patterns to exclude |

**Returns:** `str` - Filtered diff

**Example:**
```python
from commitcraft import get_diff, filter_diff

diff = get_diff()
patterns = ["*.lock", "dist/*", "*.min.js"]
filtered = filter_diff(diff, patterns)
```

---

### `clue_parser()`

Parses CommitClues from input and converts them to prompt-ready format.

**Signature:**
```python
def clue_parser(input: CommitCraftInput) -> dict[str, str | bool]
```

**Parameters:**

| Parameter | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `input` | `CommitCraftInput` | ✅ | Input with clues |

**Returns:** `dict[str, str \| bool]` - Processed clues

**Example:**
```python
from commitcraft import clue_parser, CommitCraftInput

input_data = CommitCraftInput(
    diff="...",
    bug=True,
    feat="Added dark mode"
)

clues = clue_parser(input_data)
# Result: {
#   'bug': 'This commit focus on fixing a bug',
#   'feat': 'This commit focus on a new feature: Added dark mode'
# }
```

---

## Data Models

### `CommitCraftInput`

Input data for commit message generation.

**Fields:**

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `diff` | `str` | Required | Git diff output |
| `bug` | `str \| bool` | `False` | Bug fix clue |
| `feat` | `str \| bool` | `False` | Feature clue |
| `docs` | `str \| bool` | `False` | Documentation clue |
| `refact` | `str \| bool` | `False` | Refactoring clue |
| `custom_clue` | `str \| bool` | `False` | Custom context clue |

**Example:**
```python
from commitcraft import CommitCraftInput

# Boolean clues
input1 = CommitCraftInput(diff="...", bug=True)

# Descriptive clues
input2 = CommitCraftInput(
    diff="...",
    feat="Added OAuth2 support",
    docs="Updated API documentation"
)

# Mixed
input3 = CommitCraftInput(
    diff="...",
    bug=True,
    custom_clue="Bump version to 1.0.0"
)
```

---

### `LModel`

Configuration for the AI model.

**Fields:**

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `provider` | `Provider` | `Provider.ollama` | AI provider enum |
| `model` | `str \| None` | Provider default | Model name |
| `system_prompt` | `str \| None` | `None` | Custom system prompt |
| `options` | `LModelOptions \| None` | `None` | Model options |
| `host` | `HttpUrl \| None` | `None` | API host (required for openai_compatible) |
| `api_key` | `str \| None` | `None` | API key override |

**Example:**
```python
from commitcraft import LModel, LModelOptions, Provider

# Simple
model1 = LModel(provider=Provider.ollama, model="qwen3")

# With options
model2 = LModel(
    provider=Provider.openai,
    model="gpt-4",
    options=LModelOptions(temperature=0.7, max_tokens=500),
    api_key="sk-..."
)

# OpenAI-compatible
model3 = LModel(
    provider=Provider.openai_compatible,
    model="deepseek-chat",
    host="https://api.deepseek.com",
    api_key="your-key"
)

# Ollama Cloud (cloud models end in -cloud)
model4 = LModel(
    provider=Provider.ollama_cloud,
    model="qwen3-coder:480b-cloud",
    api_key="ollama-..."
)
```

---

### `LModelOptions`

Options for model inference.

**Fields:**

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `num_ctx` | `int \| None` | Auto-calculated (Ollama) | Context window size |
| `temperature` | `float \| None` | Provider default | Sampling temperature (0.0-1.0) |
| `top_p` | `float \| None` | Provider default | Nucleus sampling probability |
| `min_ctx` | `int \| None` | `1024` | Minimum context size |
| `max_ctx` | `int \| None` | `128000` | Maximum context size |
| `max_tokens` | `int \| None` | Provider default | Maximum output tokens |
| Extra fields allowed | Any | | Provider-specific options |

**Example:**
```python
from commitcraft import LModelOptions

options = LModelOptions(
    num_ctx=8192,
    temperature=0.7,
    max_tokens=500,
    top_p=0.9  # Extra field
)
```

---

### `Provider`

Enum of supported AI providers.

**Values:**
- `Provider.ollama` - Local Ollama instance
- `Provider.ollama_cloud` - Ollama Cloud service
- `Provider.openai` - OpenAI API
- `Provider.google` - Google Gemini API
- `Provider.groq` - Groq API
- `Provider.anthropic` - Anthropic Claude models
- `Provider.openai_compatible` - OpenAI-compatible endpoints

**Example:**
```python
from commitcraft import Provider, LModel

model = LModel(provider=Provider.groq, model="llama-3.3-70b-versatile")
```

---

### `EmojiConfig`

Configuration for emoji generation.

**Fields:**

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `emoji_steps` | `EmojiSteps` | `EmojiSteps.single` | Generation mode |
| `emoji_convention` | `str` | `"simple"` | Emoji set ("simple", "full", or custom) |
| `emoji_model` | `LModel \| None` | `None` | Separate model for 2-step emoji |

**Example:**
```python
from commitcraft import EmojiConfig, EmojiSteps

config1 = EmojiConfig(
    emoji_steps=EmojiSteps.single,
    emoji_convention="simple"
)

config2 = EmojiConfig(
    emoji_steps=EmojiSteps.false  # Disable emojis
)
```

---

### `EmojiSteps`

Enum for emoji generation modes.

**Values:**
- `EmojiSteps.single` - Generate emoji and message together
- `EmojiSteps.step2` - Two-step: message first, then emoji
- `EmojiSteps.false` - Disable emoji generation

---

## Exceptions

### `MissingModelError`

Raised when `openai_compatible` provider is used without specifying a model.

**Example:**
```python
from commitcraft import LModel, Provider, MissingModelError

try:
    model = LModel(provider=Provider.openai_compatible)  # Missing model!
except MissingModelError as e:
    print(e.message)
    # "The model cannot be None for the 'openai_compatible' provider."
```

---

### `MissingHostError`

Raised when `openai_compatible` provider is used without specifying a host.

**Example:**
```python
from commitcraft import LModel, Provider, MissingHostError

try:
    model = LModel(
        provider=Provider.openai_compatible,
        model="deepseek-chat"
        # Missing host!
    )
except MissingHostError as e:
    print(e.message)
    # "The 'host' field is required and must be a valid URL..."
```

---

## Advanced Features

### Default Ignore Patterns

CommitCraft automatically excludes certain file types from diff analysis to focus on meaningful changes. Default patterns include:

```python
# Built-in default patterns
DEFAULT_IGNORE_PATTERNS = [
    # Lock files
    "*.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    # Minified/bundled assets
    "*.min.js",
    "*.min.css",
    "*.map",
    # Auto-generated files
    "*.snap",
    "*.pb.go",
    "*.pb.js",
    "*_generated.*",
    "*.d.ts",
    # Vector graphics (often large/generated)
    "*.svg",
]
```

You can customize these by creating a `.commitcraft/.ignore` file or using the `--ignore` flag.

### Generating Ignore Files

Use the interactive config wizard to generate an ignore file:

```bash
# Generate .commitcraft/.ignore with default patterns
CommitCraft config --generate-ignore
```

Or generate it manually in your scripts:

```python
from pathlib import Path

ignore_content = """# CommitCraft ignore patterns
# Files matching these patterns will be excluded from the diff sent to the LLM

# Lock files
*.lock
package-lock.json
pnpm-lock.yaml

# Minified/bundled assets
*.min.js
*.min.css
*.map

# Auto-generated files
*.snap
*.pb.go
*.pb.js
*_generated.*
*.d.ts

# Vector graphics (often large/generated)
*.svg
"""

ignore_file = Path(".commitcraft") / ".ignore"
ignore_file.parent.mkdir(exist_ok=True)
ignore_file.write_text(ignore_content)
```

---

## Complete Example: Custom Automation Script

```python
#!/usr/bin/env python3
"""
Custom script to generate commit messages with specific requirements.
"""
import subprocess
from commitcraft import (
    commit_craft,
    CommitCraftInput,
    LModel,
    Provider,
    LModelOptions,
    EmojiConfig,
    EmojiSteps,
    get_diff,
    filter_diff
)

def main():
    # Get staged diff
    diff = get_diff()

    if not diff:
        print("No staged changes found. Use 'git add' first.")
        return

    # Filter out lock files and build artifacts
    ignore_patterns = ["*.lock", "dist/*", "build/*", "node_modules/**"]
    diff = filter_diff(diff, ignore_patterns)

    # Prepare input with clues
    input_data = CommitCraftInput(
        diff=diff,
        feat="Implemented OAuth2 authentication system"  # Example clue
    )

    # Configure model
    model = LModel(
        provider=Provider.openai,
        model="gpt-4",
        options=LModelOptions(
            temperature=0.6,
            max_tokens=300
        ),
        api_key="sk-..."  # Or use env var
    )

    # Configure emojis
    emoji_config = EmojiConfig(
        emoji_steps=EmojiSteps.single,
        emoji_convention="simple"
    )

    # Context for prompt
    context = {
        "project_name": "MyAuthApp",
        "project_language": "Python",
        "project_description": "Enterprise authentication service",
        "commit_guidelines": "Use conventional commits. Limit first line to 50 chars."
    }

    # Generate commit message
    message = commit_craft(
        input=input_data,
        models=model,
        context=context,
        emoji=emoji_config
    )

    print("Generated Commit Message:")
    print("=" * 50)
    print(message)
    print("=" * 50)

    # Optionally commit automatically
    if input("Apply this commit message? (y/n): ").lower() == 'y':
        subprocess.run(["git", "commit", "-m", message])

if __name__ == "__main__":
    main()
```

---

## Type Hints

CommitCraft is fully typed. Use type checkers for better development experience:

```python
from commitcraft import commit_craft, CommitCraftInput, LModel

def generate_message(diff: str) -> str:
    input_data: CommitCraftInput = CommitCraftInput(diff=diff)
    model: LModel = LModel(provider="ollama", model="qwen3")
    message: str = commit_craft(input=input_data, models=model)
    return message
```

---

## Hook Integration

CommitCraft integrates with git hooks via the `prepare-commit-msg` hook. When installed, the hook automatically generates commit messages.

### Environment Variables

| Variable | Description | Example |
| :--- | :--- | :--- |
| `COMMITCRAFT_SKIP` | Skip CommitCraft hook for a single commit | `COMMITCRAFT_SKIP=1 git commit` |
| `COMMITCRAFT_CONFIRM` | Enable two-step confirmation mode (works in hooks even without --confirm flag) | `COMMITCRAFT_CONFIRM=1 git commit` |
| `COMMITCRAFT_CLUE_PROMPT` | Override hook's interactive mode: `1` or `true` to always prompt for CommitClues, `0` to never prompt, unset to use hook's installed mode | `COMMITCRAFT_CLUE_PROMPT=1 git commit` |
| `COMMITCRAFT_NO_EMOJI` | Disable emoji in commit messages (overrides config) | `COMMITCRAFT_NO_EMOJI=1 CommitCraft` |

### Hook Behavior

The hook automatically skips when:
- User provides their own message with `git commit -m "message"`
- `COMMITCRAFT_SKIP` environment variable is set to `1`
- User selects `[s] Skip` option in interactive mode

### Installing/Uninstalling Hooks

To manage hooks, use the CLI commands directly:

```bash
# Install local hook (interactive)
CommitCraft hook

# Install local hook (non-interactive)
CommitCraft hook --no-interactive

# Install with two-step confirmation (permanent)
CommitCraft hook --confirm

# Or use environment variable for per-commit confirmation
# (works with any hook, even without --confirm flag)
COMMITCRAFT_CONFIRM=1 git commit

# Install global hook
CommitCraft hook --global

# Uninstall local hook
CommitCraft unhook
# Or: CommitCraft hook --uninstall

# Uninstall global hook
CommitCraft unhook --global
```

### Controlling CommitClue Prompts

The `COMMITCRAFT_CLUE_PROMPT` environment variable allows you to override the hook's installed interactive mode on a per-commit basis:

**Override Modes:**
- `COMMITCRAFT_CLUE_PROMPT=1` or `COMMITCRAFT_CLUE_PROMPT=true` - Always prompt for CommitClues (enables interactive mode)
- `COMMITCRAFT_CLUE_PROMPT=0` - Never prompt for CommitClues (forces non-interactive mode)
- Unset (default) - Use the hook's installed mode (interactive or non-interactive)

**Example Usage:**

```bash
# Force interactive prompts on a non-interactive hook
COMMITCRAFT_CLUE_PROMPT=1 git commit

# Disable prompts on an interactive hook
COMMITCRAFT_CLUE_PROMPT=0 git commit

# Use hook's default behavior
git commit
```

This is particularly useful when:
- You installed a non-interactive hook but occasionally want to provide CommitClues
- You installed an interactive hook but want to skip prompts for quick commits
- You want to control interactivity without reinstalling the hook

### Dry-Run and Confirmation Modes

CommitCraft provides two modes for previewing token usage before making API calls:

**1. Dry-Run Mode (`dry_run=True`):**

Shows token usage statistics without generating a message:

```python
from commitcraft import commit_craft, CommitCraftInput, LModel, Provider

input_data = CommitCraftInput(diff=get_diff())
model = LModel(provider=Provider.openai, model="gpt-4")

# Get token usage stats
stats = commit_craft(input=input_data, models=model, dry_run=True)

print(f"Provider: {stats['provider']}")
print(f"Model: {stats['model']}")
print(f"Token Count: {stats['token_count']}")
print(f"System Prompt Tokens: {stats['system_prompt_tokens']}")
print(f"User Prompt Tokens: {stats['user_prompt_tokens']}")
```

**2. Two-Step Confirmation (CLI only):**

When using the CLI with `--confirm` flag or `COMMITCRAFT_CONFIRM=1` environment variable, CommitCraft:

1. Shows dry-run statistics
2. Prompts for user confirmation
3. Generates message only if confirmed

This mode is useful for:
- Cost control with paid providers
- Reviewing configuration before API calls
- Git hooks where you want explicit control

**Example Integration:**

```python
#!/usr/bin/env python3
"""
Script that mimics --confirm behavior in Python.
"""
from commitcraft import commit_craft, CommitCraftInput, LModel, get_diff

def generate_with_confirmation():
    diff = get_diff()
    input_data = CommitCraftInput(diff=diff)
    model = LModel(provider="openai", model="gpt-4")
    
    # Step 1: Show dry-run stats
    stats = commit_craft(input=input_data, models=model, dry_run=True)
    print("Token Usage Preview:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Step 2: Ask for confirmation
    response = input("\nProceed with commit message generation? (y/n): ")
    
    if response.lower() in ('y', 'yes'):
        # Step 3: Generate message
        message = commit_craft(input=input_data, models=model)
        return message
    else:
        print("Cancelled by user.")
        return None

if __name__ == "__main__":
    message = generate_with_confirmation()
    if message:
        print(f"\nGenerated Message:\n{message}")
```

---

## Further Reading

- [Configuration Guide](config.md) - Learn about configuration options
- [CLI Reference](cli.md) - Command-line usage
- [Recipes & Examples](recipes.md) - Advanced usage patterns
- [Troubleshooting](troubleshooting.md) - Common issues and solutions
