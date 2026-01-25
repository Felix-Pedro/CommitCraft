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
| `--dry-run` | | Calculate token usage without generating a message. | `False` |
| `--confirm` | | Enable two-step confirmation: show dry-run info, then ask for confirmation. | `False` |
| `--amend` | | Generate message for `git commit --amend`. | `False` |

### Model Configuration

Control which AI model generates your message.

| Option | Env Variable | Description | Default |
| :--- | :--- | :--- | :--- |
| `--provider` | `COMMITCRAFT_PROVIDER` | AI Provider (`ollama`, `ollama_cloud`, `groq`, `google`, `openai`, `anthropic`, `openai_compatible`). | `ollama` |
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
| `--no-emoji` | `COMMITCRAFT_NO_EMOJI` | Disable emoji in commit messages (overrides config emoji settings). | `False` |

#### Default Models by Provider

When no `--model` is specified, CommitCraft uses the following defaults:

| Provider | Default Model | Notes |
| :--- | :--- | :--- |
| `ollama` | `qwen3` | Local Ollama instance |
| `ollama_cloud` | `qwen3-coder:480b-cloud` | Ollama Cloud at https://ollama.com (cloud models end in `-cloud`) |
| `openai` | `gpt-3.5-turbo` | OpenAI API |
| `google` | `gemini-2.5-flash` | Google Gemini API |
| `groq` | `qwen/qwen3-32b` | Groq API |
| `anthropic` | **Required** | No default - must specify model (e.g., `claude-3-5-sonnet-20241022`) |
| `openai_compatible` | **Required** | No default - must specify model |

#### Provider-Specific Options Support

Different providers support different configuration options:

| Option | Ollama | Ollama Cloud | OpenAI | Google | Groq | Anthropic | OpenAI-Compatible |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `temperature` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `max_tokens` | ✅ | ✅ | ✅ | ✅ (`max_output_tokens`) | ✅ | ✅ | ✅ |
| `top_p` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `num_ctx` | ✅ (auto-calculated) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `host` | ✅ (optional) | ❌ (fixed to `https://ollama.com`) | ❌ | ❌ | ❌ | ❌ | ✅ (required) |

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

#### Dry-Run Mode (`--dry-run`)

The `--dry-run` flag calculates and displays token usage statistics **without** making an API call to generate a commit message. This is useful for:

- Estimating costs before making API calls (especially with paid providers)
- Checking if your diff is too large for the model's context window
- Verifying your configuration is working correctly
- Understanding token distribution between system prompt and user content

**Usage:**
```bash
CommitCraft --dry-run
```

**Example Output (Ollama with context sizing):**
```
                    CommitCraft Dry Run                    
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric              ┃ Value                             ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Token Count         │ 3431                              │
│ System Prompt Tokens│ 156                               │
│ User Prompt Tokens  │ 3275                              │
│ Model               │ qwen3-coder:latest                │
│ Provider            │ ollama                            │
│ Host                │ http://localhost:11434            │
│ Context Size        │ 5489                              │
│ Context Utilization │ 62.5%                             │
└─────────────────────┴───────────────────────────────────┘
```

**Example Output (Google/OpenAI/Anthropic/Groq):**
```
         CommitCraft Dry Run          
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric              ┃ Value                ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ Token Count         │ 4032                 │
│ System Prompt Tokens│ 234                  │
│ User Prompt Tokens  │ 3798                 │
│ Model               │ gemini-2.0-flash-exp │
│ Provider            │ google               │
└─────────────────────┴──────────────────────┘
```

**Plain Text Output:**

Use `--plain` or `--no-color` for JSON-style output:
```bash
CommitCraft --dry-run --plain
```

Output:
```json
{
  "token_count": 3431,
  "system_prompt_tokens": 156,
  "user_prompt_tokens": 3275,
  "model": "qwen3-coder:latest",
  "provider": "ollama",
  "host": "http://localhost:11434",
  "context_size": 5489,
  "context_utilization": "62.5%"
}
```

**Understanding the Output:**

- **Token Count:** Total tokens that will be sent to the LLM (system + user)
- **System Prompt Tokens:** Tokens from your project context, guidelines, and emoji instructions
- **User Prompt Tokens:** Tokens from the git diff and any CommitClues
- **Context Size:** (Ollama only) The calculated context window size for the request
- **Context Utilization:** (Ollama only) Percentage of context window used by the prompts

**Use Cases:**

```bash
# Check token usage before expensive API call
CommitCraft --dry-run --provider openai --model gpt-4

# Verify configuration without making a request
CommitCraft --dry-run --provider ollama --host http://remote-server:11434

# Check if diff is too large
git add .
CommitCraft --dry-run  # See if token count exceeds your model's limit

# Compare token usage across providers
CommitCraft --dry-run --provider ollama
CommitCraft --dry-run --provider google --model gemini-2.0-flash-exp
```

**Difference from `--confirm`:**

- `--dry-run`: Shows statistics and **exits** (never generates a message)
- `--confirm`: Shows statistics, **asks for confirmation**, then generates if confirmed

#### Two-Step Confirmation (`--confirm`)

The `--confirm` flag enables a two-step process that shows you a preview of the configuration and token usage before making an API call to generate the commit message. This is particularly useful when:

- Working with paid/remote LLM providers to review costs before committing
- Using git hooks where you want control over when API calls are made
- Testing configuration changes before making actual API requests
- Working with large diffs to see token counts first

**Default Behavior (no confirmation):**
```bash
CommitCraft
# Immediately generates commit message
# Output: ✨ Add user authentication system
```

**With `--confirm`:**
```bash
CommitCraft --confirm
# Step 1: Shows preview table with:
#   Token Count: 1390
#   System Prompt Tokens: 156
#   User Prompt Tokens: 1234
#   Model: qwen3
#   Provider: ollama
#   Host: http://localhost:11434
#
# Step 2: Prompts for confirmation
# Proceed with commit message generation? (y/n): y
#
# Then generates commit message
# Output: ✨ Add user authentication system
```

**Via Environment Variable:**
```bash
COMMITCRAFT_CONFIRM=1 CommitCraft
```

**In Git Hooks:**

You can enable confirmation mode in git hooks in two ways:

**1. Install hook with --confirm flag (permanent):**
```bash
# Local repository
CommitCraft hook --confirm

# Global (for all new repositories)
CommitCraft hook --global --confirm
```

**2. Use environment variable (per-commit):**
```bash
# Enable confirmation for a single commit
COMMITCRAFT_CONFIRM=1 git commit

# Or set it for your shell session
export COMMITCRAFT_CONFIRM=1
git commit  # Will use confirmation mode
```

When confirmation mode is enabled (either way), every commit will:

1. Show the commit type prompt (if interactive mode)
2. Display dry-run statistics (token usage, model, provider, host)
3. Ask "Proceed with commit message generation?"
4. Generate the message only if confirmed

**Canceling:**

If you choose "no" at the confirmation prompt, CommitCraft exits gracefully without making any API calls or charges.

**Combining with Other Flags:**

```bash
# Confirm + specific provider
CommitCraft --confirm --provider openai --model gpt-4

# Confirm + custom temperature
COMMITCRAFT_CONFIRM=1 COMMITCRAFT_TEMPERATURE=0.8 CommitCraft

# Confirm + bug fix hint
CommitCraft --confirm --bug-desc "Fixed authentication timeout"
```

**Use Cases:**

1. **Cost Control:** Review token usage before expensive API calls
   ```bash
   CommitCraft --confirm --provider openai --model gpt-4
   ```

2. **Hook Safety:** Install hooks with confirmation to avoid surprise API calls
   ```bash
   CommitCraft hook --confirm
   ```

3. **Configuration Testing:** Verify settings before committing
   ```bash
   CommitCraft --confirm --provider ollama --host http://remote-server:11434
   ```

4. **Large Diffs:** Check token count on large changesets
   ```bash
   # Stage 100+ files
   git add .
   CommitCraft --confirm  # See token count before proceeding
   ```

---

## Subcommands

CommitCraft provides several subcommands for managing configuration and git hooks:

| Command | Description |
| :--- | :--- |
| `hook` | Install CommitCraft as a git prepare-commit-msg hook |
| `unhook` | Remove CommitCraft git hook (alias for `hook --uninstall`) |
| `config` | Interactive wizard to create/edit configuration files |
| `envvars` | Display all supported environment variables with descriptions |
| `init` | (Not implemented) Initialize a new CommitCraft project |

---

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
| `--confirm` | | Enable two-step confirmation in the hook (shows dry-run preview before generating). |

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
    *   `COMMITCRAFT_CONFIRM`: Enables two-step confirmation mode (set to `1` or `true`).
    *   `COMMITCRAFT_NO_EMOJI`: Disables emoji in commit messages (set to `1` or `true`).

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

---

### `envvars`

Displays a comprehensive, categorized table of all supported environment variables.

```bash
CommitCraft envvars
```

This command shows all environment variables that can be used to configure CommitCraft, organized into the following categories:

*   **API Keys:** Authentication for various LLM providers (OpenAI, Groq, Google, Anthropic, Ollama, etc.)
*   **Provider Configuration:** Default provider and host settings
*   **Model Options:** Generation parameters like temperature, max tokens, context size
*   **Behavior & Features:** Emoji settings, confirmation mode, thinking display
*   **Output & Display:** Color output control
*   **Git Hook Settings:** Hook behavior including skip and interactive prompt control

#### Example Output

```
┌──────────────────────────────┬────────────────────────────┬──────────────────────────┐
│ Variable Name                │ Description                │ Example/Notes            │
├──────────────────────────────┼────────────────────────────┼──────────────────────────┤
│ API Keys                     │ Provider authentication    │                          │
│ OPENAI_API_KEY               │ API key for OpenAI         │ sk-...                   │
│ GROQ_API_KEY                 │ API key for Groq           │ gsk_...                  │
│ ...                          │                            │                          │
│ Git Hook Settings            │ Hook behavior config       │                          │
│ COMMITCRAFT_SKIP             │ Skip hook execution        │ COMMITCRAFT_SKIP=1       │
│ COMMITCRAFT_CLUE_PROMPT      │ Override hook interactive  │ 1/true=prompt, 0=no      │
│                              │ mode for CommitClues       │ prompt                   │
└──────────────────────────────┴────────────────────────────┴──────────────────────────┘
```

!!! tip "Quick Reference"
    Run `CommitCraft envvars` anytime to see the complete list of environment variables without checking the documentation.

!!! info "Environment Variable Files"
    All environment variables can be set in:
    
    *   `.env` file in your project root
    *   `CommitCraft.env` file in your project root
    *   Global `.env` in `~/.config/commitcraft/` (or platform-specific config directory)
    *   Your shell environment (e.g., `export COMMITCRAFT_MODEL=gpt-4` in `.bashrc`)

---

### `init`

!!! warning "Not Implemented"
    This command is currently a placeholder for future functionality to initialize a new CommitCraft project structure.
