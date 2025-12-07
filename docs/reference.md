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
from commitcraft import commit_craft, CommitCraftInput, LModel

# Get your git diff
import subprocess
diff = subprocess.run(["git", "diff", "--staged", "-M"], capture_output=True, text=True).stdout

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
) -> str
```

**Parameters:**

| Parameter | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `input` | `CommitCraftInput` | ✅ | Input containing diff and optional clues |
| `models` | `LModel` | ❌ | Model configuration (defaults to Ollama/qwen3) |
| `context` | `dict[str, str]` | ❌ | Context variables for prompt templates |
| `emoji` | `EmojiConfig \| None` | ❌ | Emoji configuration |
| `debug_prompt` | `bool` | ❌ | If True, returns prompt without calling AI |

**Returns:** `str` - Generated commit message

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

## Further Reading

- [Configuration Guide](config.md) - Learn about configuration options
- [CLI Reference](cli.md) - Command-line usage
- [Recipes & Examples](recipes.md) - Advanced usage patterns
- [Troubleshooting](troubleshooting.md) - Common issues and solutions
