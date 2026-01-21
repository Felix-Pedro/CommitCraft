# CLI Reference

CommitCraft is a powerful command-line interface tool. This page details all available commands, arguments, and options.

!!! info "Usage"
    The main entry point is `CommitCraft`. You can also run it via python using `python -m commitcraft`.

---

## Main Command

The main command generates a commit message based on your staged changes.

```bash
CommitCraft [OPTIONS] [COMMAND]
```

### Core Options

| Option | Short | Description | Default |
| :--- | :--- | :--- | :--- |
| `--version` | `-v` | Show the current version and exit. | |
| `--no-color` | `-p` | Disable colored output (useful for piping/scripts). | `False` |
| `--config-file` | | Path to a custom config file (`.toml`, `.yaml`, `.json`). | Checks `.commitcraft/` folder |
| `--ignore` | | Comma-separated list of file patterns to exclude from the diff. | Checks `.commitcraft/.ignore` with default patterns |
| `--debug-prompt` | | Print the generated prompt without sending it to the LLM. | `False` |
| `--amend` | | Generate message for `git commit --amend`. | `False` |

### Model Configuration

Control which AI model generates your message.

| Option | Env Variable | Description | Default |
| :--- | :--- | :--- | :--- |
| `--provider` | `COMMITCRAFT_PROVIDER` | AI Provider (`ollama`, `ollama_cloud`, `groq`, `google`, `openai`, `openai_compatible`). | `ollama` |
| `--model` | `COMMITCRAFT_MODEL` | Specific model name (e.g., `llama3`, `gpt-4`). | Provider dependent (see table below) |
| `--system-prompt` | `COMMITCRAFT_SYSTEM_PROMPT` | Override the default system prompt. | |
| `--temperature` | `COMMITCRAFT_TEMPERATURE` | Creativity level (0.0 - 1.0). | Config dependent |
| `--top-p` | `COMMITCRAFT_TOP_P` | Nucleus sampling probability (0.0 - 1.0). | Config dependent |
| `--min-ctx` | `COMMITCRAFT_MIN_CONTEXT_SIZE` | Minimum context size for auto-calculation. | `1024` |
| `--max-ctx` | `COMMITCRAFT_MAX_CONTEXT_SIZE` | Maximum context size for auto-calculation. | `128000` |
| `--num-ctx` | `COMMITCRAFT_NUM_CTX` | Context window size (token limit). Ollama only. | Auto-calculated for Ollama |
| `--max-tokens` | `COMMITCRAFT_MAX_TOKENS` | Maximum number of tokens to generate. | Config dependent |
| `--host` | `COMMITCRAFT_HOST` | API host URL (required for `openai_compatible`, optional for `ollama`). | `http://localhost:11434` (Ollama) |
| `--show-thinking` | `COMMITCRAFT_SHOW_THINKING` | Display the model's "Chain of Thought" if available (e.g., DeepSeek R1). | `False` |

#### Default Models by Provider

When no `--model` is specified, CommitCraft uses the following defaults:

| Provider | Default Model | Notes |
| :--- | :--- | :--- |
| `ollama` | `qwen3` | Local Ollama instance |
| `ollama_cloud` | `qwen3-coder:480b-cloud` | Ollama Cloud at https://ollama.com (cloud models end in `-cloud`) |
| `openai` | `gpt-3.5-turbo` | OpenAI API |
| `google` | `gemini-2.5-flash` | Google Gemini API |
| `groq` | `qwen/qwen3-32b` | Groq API |
| `openai_compatible` | **Required** | No default - must specify model |

#### Provider-Specific Options Support

Different providers support different configuration options:

| Option | Ollama | Ollama Cloud | OpenAI | Google | Groq | OpenAI-Compatible |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `temperature` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `max_tokens` | ✅ | ✅ | ✅ | ✅ (`max_output_tokens`) | ✅ | ✅ |
| `top_p` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `num_ctx` | ✅ (auto-calculated) | ❌ | ❌ | ❌ | ❌ | ❌ |
| `host` | ✅ (optional) | ❌ (fixed to `https://ollama.com`) | ❌ | ❌ | ❌ | ✅ (required) |

**Notes:**
- **Ollama** auto-calculates `num_ctx` based on diff size if not specified (min: 1024, max: 128000)
- **Ollama Cloud** uses the chat API and does not support `num_ctx` or custom hosts
- **Google** maps `max_tokens` to `max_output_tokens` internally
- **OpenAI-compatible** requires both `--model` and `--host` to be specified

### Default Context Options

Customize project-specific information used in prompt generation.

| Option | Env Variable | Description | Default |
| :--- | :--- | :--- | :--- |
| `--project-name` | `COMMITCRAFT_PROJECT_NAME` | Project name for context | None |
| `--project-language` | `COMMITCRAFT_PROJECT_LANGUAGE` | Primary programming language | None |
| `--project-description` | `COMMITCRAFT_PROJECT_DESCRIPTION` | Brief project description | None |
| `--commit-guide` | `COMMITCRAFT_COMMIT_GUIDE` | Custom commit guidelines | See defaults |

These values are injected into the system prompt using Jinja2 templating. See [Context Variables](config.md#context-variables-template-syntax) for details.

### CommitClues

Help the AI understand *why* you made changes.

| Option | Description |
| :--- | :--- |
| `--bug` / `--bug-desc` | Signal a bug fix. Use `--bug-desc "Fixed X"` for details. |
| `--feat` / `--feat-desc` | Signal a new feature. Use `--feat-desc "Added Y"` for details. |
| `--docs` / `--docs-desc` | Signal documentation changes. |
| `--refact` / `--refact-desc` | Signal code refactoring. |
| `--context-clue` | Provide a free-form custom hint (e.g., "Bump version to 1.0"). |

See the [CommitClues Guide](recipes.md#using-commitclues) for detailed usage examples and best practices.

### Advanced Features

#### Model Thinking Process (`--show-thinking`)

Some advanced AI models (like DeepSeek R1, QwQ, and other reasoning models) include a "chain of thought" or thinking process in their responses, enclosed in `<think>...</think>` tags. By default, CommitCraft hides this internal reasoning and only shows the final commit message.

**Default Behavior (thinking hidden):**
```bash
CommitCraft
# Output: ✨ Add user authentication system
```

**With `--show-thinking`:**
```bash
CommitCraft --show-thinking
# Output:
# <think>
# Let me analyze this diff. I see changes in auth.py, login.html, and middleware.
# This appears to be adding JWT-based authentication with session management.
# The commit introduces a new feature, so I'll use ✨ emoji...
# </think>
#
# ✨ Add user authentication system
```

**When to use:**
- **Debugging prompts:** See how the model interprets your diff
- **Understanding reasoning:** Learn why the model chose specific wording
- **Model comparison:** Compare reasoning quality across different models
- **Verbose mode:** When you want full transparency into AI decision-making

**Supported Models:**
- DeepSeek R1 / R1-Distill
- QwQ (Qwen reasoning model)
- Other models that output `<think>` tags

**Note:** Models without thinking capabilities will not output anything different with this flag.

---

## Subcommands

### `hook`

Sets up CommitCraft as a git `prepare-commit-msg` hook. This integrates CommitCraft directly into your `git commit` workflow.

```bash
CommitCraft hook [OPTIONS]
```

When installed, running `git commit` will automatically generate a message and pre-fill your editor.

#### Modes

*   **Interactive (Default):** The hook will ask you for "CommitClues" (bug, feature, etc.) right in the terminal before generating the message.
*   **Non-interactive:** The hook runs silently in the background using default settings.

#### Options

| Option | Short | Description |
| :--- | :--- | :--- |
| `--global` | `-g` | Install as a **global** git hook template for all *new* repositories. |
| `--uninstall` | `-u` | Remove the CommitCraft hook from the current (or global) repository. |
| `--no-interactive` | | Disable the interactive prompts during commit. |

#### Skipping the Hook

You can skip the CommitCraft hook in several ways:

**1. Environment Variable:**
```bash
COMMITCRAFT_SKIP=1 git commit
```

**2. Interactive Menu:**
When using interactive mode, choose `[s] Skip (write message manually)` from the menu.

**3. Auto-Skip on `-m` Flag:**
The hook automatically skips when you provide your own message:
```bash
git commit -m "Your custom message"
```

**4. Uninstall:**
```bash
# Remove local hook
CommitCraft unhook
# Or: CommitCraft hook --uninstall

# Remove global hook
CommitCraft unhook --global
```

---

### `unhook`

Convenient alias for removing CommitCraft hooks. This command is equivalent to `CommitCraft hook --uninstall`.

```bash
CommitCraft unhook [OPTIONS]
```

#### Options

| Option | Short | Description |
| :--- | :--- | :--- |
| `--global` | `-g` | Remove the **global** git hook template (instead of local). |

!!! example "Workflow"
    1. Run `CommitCraft hook` in your repo.
    2. Stage files: `git add .`
    3. Commit: `git commit`
    4. Answer the prompt: "Is this a bug fix? (y/n)"
    5. Review the generated message in your editor.

### Temporary Overrides for Hooks

When using the `CommitCraft hook`, you might sometimes want to temporarily use a different model, provider, or other setting without changing your permanent configuration files. You can achieve this by setting environment variables directly before your `git commit` command.

CommitCraft respects environment variables for most of its configuration options. The variable names generally correspond to the CLI argument names (e.g., `COMMITCRAFT_MODEL` for `--model`).

!!! info "Example: Temporarily change model"
    ```bash
    COMMITCRAFT_MODEL=gemma2 git commit -m "feat: use gemma2 for this commit"
    ```
    In this example, the hook will use the `gemma2` model for *this specific commit only*, ignoring the model specified in your config files.

!!! tip "Common Environment Variables"
    *   `COMMITCRAFT_MODEL`: Overrides the default model.
    *   `COMMITCRAFT_PROVIDER`: Overrides the default provider.
    *   `COMMITCRAFT_TEMPERATURE`: Overrides the model temperature.
    *   `COMMITCRAFT_HOST`: Overrides the host for API calls.

This method is especially useful for one-off commits where specific model behavior is desired.


### `config`

Launches an interactive wizard to create configuration files.

```bash
CommitCraft config [OPTIONS]
```

#### Options

| Option | Short | Description |
| :--- | :--- | :--- |
| `--generate-ignore` | `-i` | Generate a `.commitcraft/.ignore` file with default patterns. |

This wizard helps you set up:
*   **Providers:** Configure API keys and endpoints for Ollama, OpenAI, etc.
*   **Models:** Select your preferred default model.
*   **Context:** Define project description and guidelines.
*   **Emojis:** Choose your preferred emoji style (gitmoji, simple, etc.).
*   **Ignore Patterns:** Automatically create an ignore file with default patterns for lock files, minified assets, and generated code.

#### Default Ignore Patterns

When you generate an ignore file, it includes these default patterns:

```bash
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
```

You can edit the generated `.commitcraft/.ignore` file to add or remove patterns as needed.

### `init`

!!! warning "Not Implemented"
    This command is currently a placeholder for future functionality to initialize a new CommitCraft project structure.