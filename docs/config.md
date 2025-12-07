# Configuration

CommitCraft can be configured via `toml`, `yaml`, or `json` files.

## Configuration File Locations

CommitCraft looks for configuration in the following order:

1. Local `.commitcraft/context.toml` (or .yaml, .json)
2. Global `~/.commitcraft/context.toml`

## Environment Variables (.env)

For API keys and sensitive configuration, CommitCraft uses either a `.env` file in the execution directory or system-wide environment variables.

### Standard Providers

```sh
# Ollama (optional - only needed for Ollama Cloud or remote instances)
OLLAMA_HOST=http://localhost:11434
OLLAMA_API_KEY=your-api-key-here  # For Ollama Cloud

# Commercial Providers
OPENAI_API_KEY=sk-your-api-key-here
GROQ_API_KEY=gsk_your-api-key-here
GOOGLE_API_KEY=your-google-api-key

# Custom OpenAI-compatible providers (if not using named profiles)
CUSTOM_API_KEY=your-custom-api-key
```

### Named Provider Profiles

For named providers (configured in `[providers.nickname]` sections), use the pattern `NICKNAME_API_KEY`:

```sh
# For [providers.remote_ollama]
REMOTE_OLLAMA_API_KEY=your-remote-ollama-key

# For [providers.deepseek]
DEEPSEEK_API_KEY=your-deepseek-api-key

# For [providers.litellm]
LITELLM_API_KEY=your-litellm-key
```

The interactive config wizard (`CommitCraft config`) will help you set up these environment variables automatically.

---

## Context Variables & Template Syntax

CommitCraft uses **Jinja2** templating in system prompts, allowing you to inject project-specific information dynamically. This helps the AI generate commit messages that are contextually aware of your project.

### Available Context Variables

You can define these variables in your configuration file or via CLI, and reference them in your `system_prompt` using Jinja2 syntax:

| Variable | Description | Config Section | CLI Flag |
| :--- | :--- | :--- | :--- |
| `{{ project_name }}` | Name of your project | `[context]` | `--project-name` |
| `{{ project_language }}` | Primary programming language | `[context]` | `--project-language` |
| `{{ project_description }}` | Brief project description | `[context]` | `--project-description` |
| `{{ commit_guidelines }}` | Custom commit message guidelines | `[context]` | `--commit-guide` |

### Configuration Example

**File: `.commitcraft/config.toml`**

```toml
[context]
project_name = "MyAwesomeApp"
project_language = "Python"
project_description = "A web application for managing tasks and projects"
commit_guidelines = """
- Use imperative mood (Add, Fix, Update)
- Reference issue numbers when applicable
- Keep first line under 50 characters
- Explain 'why' in the body, not 'what'
"""

[models]
system_prompt = """
You are a commit message generator for {{ project_name }},
a project written in {{ project_language }}.

{{ project_description }}

Follow these commit guidelines:
{{ commit_guidelines }}

Generate concise, informative commit messages based on the provided diff.
"""
provider = "ollama"
model = "qwen3"
```

### Default System Prompt Template

CommitCraft's default system prompt already uses context variables:

```jinja2
# Proposure

You are a commit message helper {% if project_name or project_language %} for {{ project_name }} {% if project_language %} a project written in {{ project_language }} {% endif %} {% endif %} {% if project_description %} described as:

{{ project_description }}

{% else %}.
{% endif %}
Your only task is to receive a git diff and maybe some clues, then return a simple commit message following these guidelines:

{{ commit_guidelines }}
```

This template:
- Conditionally includes project name and language if provided
- Includes project description if available
- Always includes commit guidelines (uses defaults if not specified)

### CLI Override

You can override context variables for a single commit:

```bash
CommitCraft --project-name "TempProject" --project-language "TypeScript" --commit-guide "Use conventional commits format"
```

### Jinja2 Template Features

You can use standard Jinja2 features in your custom system prompts:

**Conditionals:**
```jinja2
{% if project_language == "Python" %}
Follow PEP 8 naming conventions in commit messages.
{% endif %}
```

**Loops (if using custom context):**
```jinja2
{% for guideline in guidelines_list %}
- {{ guideline }}
{% endfor %}
```

**Filters:**
```jinja2
{{ project_name | upper }}  # MYAWESOMEAPP
{{ project_description | truncate(50) }}
```

### Best Practices

1. **Set context at the project level** - Define in `.commitcraft/config.toml` for consistent messages across the team
2. **Keep descriptions concise** - The AI doesn't need your entire README; 1-2 sentences suffice
3. **Use specific guidelines** - Generic guidelines like "be clear" don't help; specify format, length, style
4. **Don't repeat yourself** - Context variables are for dynamic content; static instructions go directly in `system_prompt`

---

## Example Configuration

```toml
[context]
project_name = "CommitCraft"
project_language = "Python"
commit_guidelines = "Follow conventional commits. Keep first line under 72 characters."

[models]
system_prompt = "You are a helpful assistant..."
provider = "ollama"
model = "llama3"
```

## Emoji Configuration

CommitCraft supports GitMoji conventions to add emojis to your commit messages. You can configure emoji behavior in the `[emoji]` section of your configuration file.

### Configuration Options

```toml
[emoji]
emoji_steps = "single"      # Options: "single", "2-step", or false
emoji_convention = "simple"  # Options: "simple", "full", or custom string
```

#### `emoji_steps`

Controls how emojis are generated:

- **`"single"`** (default): The AI generates the commit message and emoji in one step. The emoji guidelines are appended to the system prompt, and the model chooses the appropriate emoji while writing the commit message.

- **`"2-step"`**: First generates the commit message without emoji, then in a second AI call, selects the appropriate emoji based on the message. This uses more API calls but may provide more consistent emoji selection.

- **`false`**: Disables emoji generation entirely. Commit messages will not include emojis.

#### `emoji_convention`

Defines which emoji set to use:

- **`"simple"`** (default): A curated subset of the most common GitMoji emojis (37 emojis). Best for most projects.

  Includes: ⚡️ (performance), 🐛 (bug fix), 🚑️ (hotfix), ✨ (new feature), 📝 (docs), ✅ (tests), 🔒️ (security), 🔖 (release), 🚨 (linter warnings), ⬇️⬆️ (dependencies), ♻️ (refactor), ➕➖ (add/remove dependency), 🔧 (config), 🌐 (i18n), ✏️ (typos), 🚚 (move/rename), 💥 (breaking changes), 🍱 (assets), ♿️ (accessibility), 💡 (comments), 🗃️ (database), 🚸 (UX), 🏗️ (architecture), 🤡 (mocks), 🥚 (easter egg), 🙈 (.gitignore), 📸 (snapshots), ⚗️ (experiments), 🏷️ (types), 🥅 (error handling), 🧐 (data exploration), ⚰️ (dead code), 🧪 (failing test), 👔 (business logic), 🩺 (healthcheck), 💸 (sponsorship)

- **`"full"`**: The complete GitMoji specification (58 emojis). Provides more granular emoji options for specialized use cases.

  Includes all emojis from "simple" plus: 🎨 (code structure), 🔥 (remove code), 🚀 (deployment), 💄 (UI/styles), 🎉 (initial commit), 🔐 (secrets), 🚧 (WIP), 💚 (CI fix), 📌 (pin dependencies), 👷 (CI build), 📈 (analytics), 🔨 (dev scripts), 💩 (bad code), ⏪️ (revert), 🔀 (merge), 📦️ (compiled files), 👽️ (external API), 📄 (license), 💬 (text/literals), 🔊🔇 (logs), 👥 (contributors), 📱 (responsive), 🔍️ (SEO), 🌱 (seed files), 🚩 (feature flags), 💫 (animations), 🗑️ (deprecation), 🛂 (authorization), 🩹 (simple fix), 🧱 (infrastructure), 🧑‍💻 (developer experience), 🧵 (multithreading), 🦺 (validation)

- **Custom string**: Provide your own emoji guidelines as a string. The string will be appended to the system prompt.

  Example:
  ```toml
  [emoji]
  emoji_steps = "single"
  emoji_convention = """
  Use these emojis for commits:
  🔨 - Build/tooling changes
  🎯 - Focus/scope improvements
  🌟 - Major milestones
  Format: {emoji} {message}
  """
  ```

### Emoji Output Format

When emojis are enabled, the commit message title will be formatted as:

```
{emoji} {commit title}
```

Example output:
```
✨ Add dark mode toggle to user settings

- Implemented theme switching logic
- Added persistence to localStorage
- Updated CSS variables for dark theme
```

### CLI Override

You can disable emojis for a single commit using the `--no-emoji` flag (if implemented), or by setting `emoji_steps = false` in your configuration.

### Best Practices

- **Use `"simple"`** for general projects - it covers 95% of common commit types
- **Use `"full"`** if your project has specific needs (CI/CD, infrastructure, analytics)
- **Use `"single"` step** for faster generation and lower API costs
- **Use `"2-step"`** if you find emoji selection inconsistent with your provider

---

## Named Provider Profiles

Named provider profiles allow you to configure multiple instances of providers with different settings. This is useful for managing local vs. remote instances, multiple API endpoints, or different model configurations.

### Configuration

Define named providers in the `[providers.nickname]` section:

```toml
# Default provider (used when no --provider specified)
[models]
provider = "ollama"
model = "qwen3"

# Named provider profiles
[providers.remote_ollama]
provider = "ollama"
model = "llama3"
host = "https://my-ollama-server.example.com"

[providers.remote_ollama.options]
temperature = 0.7
max_tokens = 500

[providers.deepseek]
provider = "openai_compatible"
model = "deepseek-chat"
host = "https://api.deepseek.com"

[providers.deepseek.options]
temperature = 0.5

[providers.groq_fast]
provider = "groq"
model = "llama-3.3-70b-versatile"

[providers.groq_fast.options]
temperature = 0.3
max_tokens = 300
```

### API Keys for Named Providers

API keys for named providers use the format `NICKNAME_API_KEY` (uppercase):

```bash
# .env or CommitCraft.env
REMOTE_OLLAMA_API_KEY=your-remote-ollama-key
DEEPSEEK_API_KEY=your-deepseek-key
GROQ_FAST_API_KEY=your-groq-key
```

### Using Named Providers via CLI

Specify the named provider with the `--provider` flag:

```bash
# Use the remote_ollama profile
CommitCraft --provider remote_ollama

# Use the deepseek profile
CommitCraft --provider deepseek

# Use the groq_fast profile
CommitCraft --provider groq_fast
```

### Real-World Examples

**Multiple Ollama Instances:**
```toml
[models]
provider = "ollama"  # Local by default
model = "qwen3"

[providers.work_ollama]
provider = "ollama"
model = "llama3"
host = "https://ollama.work.com"

[providers.home_ollama]
provider = "ollama"
model = "gemma2"
host = "http://192.168.1.100:11434"
```

**Multiple OpenAI-Compatible Services:**
```toml
[providers.deepseek]
provider = "openai_compatible"
model = "deepseek-chat"
host = "https://api.deepseek.com"

[providers.together]
provider = "openai_compatible"
model = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
host = "https://api.together.xyz/v1"

[providers.litellm]
provider = "openai_compatible"
model = "claude-3-5-sonnet-20241022"
host = "http://localhost:4000"  # LiteLLM proxy
```

**Mixed Providers for Different Use Cases:**
```toml
# Fast, cheap commits
[providers.quick]
provider = "groq"
model = "qwen/qwen3-32b"

[providers.quick.options]
temperature = 0.2
max_tokens = 200

# High-quality, detailed commits
[providers.detailed]
provider = "openai"
model = "gpt-4"

[providers.detailed.options]
temperature = 0.7
max_tokens = 1000
```

### Configuration Precedence

When using named providers, CommitCraft merges configurations in this order (highest to lowest priority):

1. **CLI arguments** (e.g., `--temperature 0.5`)
2. **Named provider profile** (e.g., `[providers.deepseek]`)
3. **Default models block** (e.g., `[models]`)
4. **Global config** (`~/.config/commitcraft/`)
5. **Built-in defaults**

---

## Configuration Precedence & Merging

Understanding how CommitCraft merges configurations helps avoid unexpected behavior when using multiple config sources.

### Hierarchy (Highest to Lowest Priority)

1. **CLI Arguments** - Flags passed directly to the command
2. **Project Configuration** - `.commitcraft/config.toml` in current repo
3. **Global Configuration** - `~/.config/commitcraft/config.toml` (or OS-specific app directory)
4. **Built-in Defaults** - Hardcoded defaults in CommitCraft

### Within Each Level

Within a single configuration level (e.g., project config), the priority is:

1. **CLI arguments** (if at that level)
2. **`[models]` block** (the default provider)
3. **`[providers.nickname]` blocks** (only used when explicitly selected with `--provider nickname`)

### Merging Behavior

**Shallow Merge:** Top-level keys are replaced, not merged deeply.

**Example:**

**Global config (`~/.config/commitcraft/config.toml`):**
```toml
[models]
provider = "ollama"
model = "qwen3"
temperature = 0.7

[context]
project_name = "MyProject"
commit_guidelines = "Use conventional commits"
```

**Project config (`.commitcraft/config.toml`):**
```toml
[models]
provider = "openai"
model = "gpt-4"
# temperature not specified

[context]
project_name = "SpecificProject"
# commit_guidelines not specified
```

**Result when running `CommitCraft` in the project directory:**
```toml
[models]
provider = "openai"        # From project
model = "gpt-4"            # From project
temperature = 0.7          # From global (merged)

[context]
project_name = "SpecificProject"  # From project
commit_guidelines = "Use conventional commits"  # From global (merged)
```

### Practical Examples

**Override just the model for one commit:**
```bash
# Project config uses ollama/qwen3
CommitCraft --model gemma2
# Uses: ollama/gemma2 (provider from config, model from CLI)
```

**Switch to a completely different provider:**
```bash
# Project config uses ollama
CommitCraft --provider openai --model gpt-4
# Uses: openai/gpt-4 (both from CLI)
```

**Use named provider but override temperature:**
```bash
CommitCraft --provider deepseek --temperature 0.9
# Uses: deepseek provider config + temperature override
```

### Best Practices

1. **Global for user preferences** - Your preferred provider, API keys, personal style
2. **Project for team standards** - Shared commit guidelines, emoji conventions, ignore patterns
3. **CLI for one-off changes** - Quick model swaps, testing different providers
4. **Named providers for contexts** - Work vs. personal, fast vs. detailed, local vs. cloud

---

## Environment Variables Reference

CommitCraft supports environment variables for all configuration options. This is useful for CI/CD, scripting, or temporary overrides without modifying config files.

### Configuration Variables

| Variable | Equivalent CLI Flag | Description | Example |
| :--- | :--- | :--- | :--- |
| `COMMITCRAFT_PROVIDER` | `--provider` | AI provider | `ollama`, `openai`, `groq` |
| `COMMITCRAFT_MODEL` | `--model` | Model name | `qwen3`, `gpt-4` |
| `COMMITCRAFT_SYSTEM_PROMPT` | `--system-prompt` | Custom system prompt | `"You are..."` |
| `COMMITCRAFT_TEMPERATURE` | `--temperature` | Model temperature | `0.7` |
| `COMMITCRAFT_NUM_CTX` | `--num-ctx` | Context window (Ollama) | `8192` |
| `COMMITCRAFT_MAX_TOKENS` | `--max-tokens` | Max output tokens | `500` |
| `COMMITCRAFT_HOST` | `--host` | API host URL | `http://localhost:11434` |
| `COMMITCRAFT_SHOW_THINKING` | `--show-thinking` | Show thinking tags | `true`, `false` |
| `COMMITCRAFT_PROJECT_NAME` | `--project-name` | Project name | `MyApp` |
| `COMMITCRAFT_PROJECT_LANGUAGE` | `--project-language` | Language | `Python` |
| `COMMITCRAFT_PROJECT_DESCRIPTION` | `--project-description` | Description | `"A web app..."` |
| `COMMITCRAFT_COMMIT_GUIDE` | `--commit-guide` | Commit guidelines | `"Use imperative..."` |

### API Keys

| Variable | Provider | Description |
| :--- | :--- | :--- |
| `OLLAMA_HOST` | Ollama (local) | Ollama host URL |
| `OLLAMA_API_KEY` | Ollama Cloud / Remote | API key for authenticated Ollama instances |
| `OPENAI_API_KEY` | OpenAI | OpenAI API key |
| `GROQ_API_KEY` | Groq | Groq API key |
| `GOOGLE_API_KEY` | Google | Google Gemini API key |
| `CUSTOM_API_KEY` | OpenAI-compatible | Generic API key for custom providers |
| `{NICKNAME}_API_KEY` | Named providers | API key for named provider (uppercase nickname) |

### Output Control

| Variable | Description | Values |
| :--- | :--- | :--- |
| `NO_COLOR` | Disable all colored output | `1`, `true` |
| `FORCE_COLOR` | Force colored output (default) | `1`, `true` |

### Usage Examples

**Temporary model override:**
```bash
COMMITCRAFT_MODEL=gemma2 CommitCraft
```

**Use different provider for one commit:**
```bash
COMMITCRAFT_PROVIDER=groq COMMITCRAFT_MODEL=llama-3.3-70b-versatile CommitCraft
```

**CI/CD environment:**
```bash
export COMMITCRAFT_PROVIDER=openai
export COMMITCRAFT_MODEL=gpt-3.5-turbo
export OPENAI_API_KEY=${{ secrets.OPENAI_KEY }}
export NO_COLOR=1  # Disable colors for log parsing
CommitCraft
```

**Git hook with temporary override:**
```bash
# In your hook script
COMMITCRAFT_TEMPERATURE=0.3 CommitCraft
```

---

## Ollama Cloud Setup Guide

**Ollama Cloud** provides cloud-hosted access to Ollama models without requiring local GPU resources. CommitCraft has native support via the `ollama_cloud` provider.

### Step 1: Get Your API Key

1. Visit [ollama.com](https://ollama.com)
2. Sign in or create an account
3. Navigate to [Settings > Keys](https://ollama.com/settings/keys)
4. Generate a new API key
5. Copy the key (it starts with `ollama-`)

### Step 2: Set Up Environment Variable

**Option A: Using `.env` file**
```bash
# Create or edit .env in your project directory
echo "OLLAMA_API_KEY=ollama-your-api-key-here" >> .env
```

**Option B: Using CommitCraft.env**
```bash
echo "OLLAMA_API_KEY=ollama-your-api-key-here" >> CommitCraft.env
```

**Option C: System environment variable**
```bash
# Linux/macOS (add to ~/.bashrc or ~/.zshrc)
export OLLAMA_API_KEY=ollama-your-api-key-here

# Windows (PowerShell)
$env:OLLAMA_API_KEY="ollama-your-api-key-here"
```

### Step 3: Configure CommitCraft

**Using interactive config wizard (recommended):**
```bash
CommitCraft config
# Select "ollama_cloud" when prompted for provider
# Enter your API key when prompted
```

**Manual configuration:**
```toml
# .commitcraft/config.toml or ~/.config/commitcraft/config.toml
[models]
provider = "ollama_cloud"
model = "qwen3-coder:480b-cloud"  # Cloud models end in -cloud

[models.options]
temperature = 0.7
max_tokens = 500
```

### Step 4: Test Your Setup

```bash
# Stage some changes
git add .

# Generate a commit message
CommitCraft --provider ollama_cloud

# Or use the debug mode to verify configuration
CommitCraft --provider ollama_cloud --debug-prompt
```

### Available Models

Ollama Cloud supports various models. **Important:** All cloud models end with `-cloud` suffix.

Common options:
- `qwen3-coder:480b-cloud` - Large coding model (default)
- `llama3:70b-cloud` - Meta's Llama 3 70B
- `gemma2:27b-cloud` - Google's Gemma 2 27B
- `mistral:7b-cloud` - Mistral AI 7B
- And many more...

Check [ollama.com/library](https://ollama.com/library) and filter for cloud-compatible models (look for the `-cloud` suffix).

### Differences from Local Ollama

| Feature | Local Ollama | Ollama Cloud |
| :--- | :---: | :---: |
| Requires GPU | ✅ | ❌ |
| Internet required | ❌ | ✅ |
| API key required | ❌ | ✅ |
| Host configuration | Custom | Fixed (`https://ollama.com`) |
| `num_ctx` support | ✅ | ❌ |
| API type | `generate` | `chat` |
| Privacy | Fully local | [See privacy policy](https://ollama.com/cloud) |

### Troubleshooting

**Error: "Unauthorized" or 401**
- Verify your API key is correct
- Check that `OLLAMA_API_KEY` is set
- Regenerate key if necessary

**Error: "Model not found"**
- Ensure the model name is valid for Ollama Cloud and ends with `-cloud` suffix
- Try `qwen3-coder:480b-cloud` as a known working model
- Local model names (like `qwen3`) won't work with Ollama Cloud

**Slow response times**
- Ollama Cloud models may have queues during high usage
- Consider using a local instance for faster responses

### Pricing

Ollama Cloud offers a free tier for personal use. See [ollama.com/pricing](https://ollama.com/pricing) for current limits and paid plans.

---

## Ignoring Files (`.commitcraft/.ignore`)

You can exclude files from the diff analysis by creating a `.commitcraft/.ignore` file with patterns (similar to `.gitignore`). This is useful for preventing CommitCraft from analyzing files that are not relevant to commit messages (e.g., build artifacts, temporary files, generated code).

### Pattern Syntax

CommitCraft uses **fnmatch** patterns (like shell globbing):

| Pattern | Matches | Example |
| :--- | :--- | :--- |
| `*.ext` | Files with extension | `*.pyc`, `*.min.js` |
| `filename` | Exact filename anywhere | `package-lock.json` |
| `dir/*` | All files in directory | `dist/*`, `build/*` |
| `dir/**` | Recursively in directory | `node_modules/**` |
| `**/pattern` | Pattern at any depth | `**/*.test.js` |
| `prefix*` | Files starting with | `test_*`, `temp*` |

### Language-Specific Examples

**Python:**
```
# .commitcraft/.ignore
*.pyc
__pycache__/*
*.pyo
*.egg-info/*
.pytest_cache/*
.coverage
htmlcov/*
dist/*
build/*
*.whl
venv/*
.venv/*
poetry.lock
Pipfile.lock
```

**JavaScript/TypeScript:**
```
# .commitcraft/.ignore
node_modules/**
package-lock.json
yarn.lock
pnpm-lock.yaml
dist/*
build/*
*.min.js
*.min.css
.next/*
.nuxt/*
coverage/*
.cache/*
```

**Rust:**
```
# .commitcraft/.ignore
target/*
Cargo.lock
*.rlib
*.rmeta
```

**Go:**
```
# .commitcraft/.ignore
vendor/*
go.sum
*.exe
*.test
*.out
```

**General (any project):**
```
# .commitcraft/.ignore
# Lock files
*.lock
package-lock.json
poetry.lock
Gemfile.lock

# Build artifacts
dist/*
build/*
out/*
*.min.js
*.min.css

# Dependencies
node_modules/**
vendor/**
venv/*

# IDE files
.idea/*
.vscode/*
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Generated code
*_pb2.py
*.generated.ts
```

### CLI Alternative

Use the `--ignore` flag for one-time exclusions:

```bash
# Single pattern
CommitCraft --ignore "*.lock"

# Multiple patterns (comma-separated)
CommitCraft --ignore "*.lock,dist/*,node_modules/**"

# Complex example
CommitCraft --ignore "*.min.js,*.map,build/*,coverage/*"
```

### Best Practices

1. **Exclude lock files** - Dependency lock files rarely need meaningful commit messages
2. **Exclude generated code** - Protocol buffers, GraphQL schemas, build artifacts, etc.
3. **Exclude minified files** - Minified JS/CSS doesn't help the AI generate good messages
4. **Keep ignore files minimal** - Only exclude files that add noise, not legitimate changes
5. **Use project-level ignores** - Commit `.commitcraft/.ignore` to share patterns with your team

### How Filtering Works

When you run CommitCraft:
1. Gets the full diff from `git diff --staged -M`
2. Parses each file path in the diff
3. Checks if it matches any ignore pattern
4. Removes matched files from the diff
5. Sends the filtered diff to the AI

This means ignored files won't influence the generated commit message at all.