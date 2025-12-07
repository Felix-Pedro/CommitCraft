# Default Values Reference

This page documents all default values used by CommitCraft, defined in `src/commitcraft/defaults.py`.

## Default Commit Guidelines

CommitCraft uses the following guidelines by default when generating commit messages:

```
- Never ask for folow-up questions.
- Don't ask quetions.
- Don't talk about yourself.
- Be concise and clear.
- Be informative.
- Don't explain row by row just the global goal of the changes.
- Avoid unecessary details and long explanations.
- Use action verbs.
- Use bullet points in the body if there are many changes
- Do not talk about the hashes.
- Create concise and comprehensive commit messages.
- Be direct about what changed and why. Focous on what.
- Give a small summary of what has changed and how it may afect the rest of the project.
- Do not return any explanation other then the commit message itself.
- If there are many changes focous on the main ones.
- The first row shall be te title of your message, so make it simple and informative.
- Do not introduce your message!
```

**Override:** Set `commit_guidelines` in `[context]` section of your config.

---

## Default System Prompt Template

```jinja2
# Proposure

You are a commit message helper {% if project_name or project_language %} for {{ project_name }} {% if project_language %} a project written in {{ project_language }} {% endif %} {% endif %} {% if project_description %} described as:

{{ project_description }}

{% else %}.
{% endif %}
Your only task is to receive a git diff and maybe some clues, then return a simple commit message following these guidelines:

{{ commit_guidelines }}
```

**Features:**
- Uses Jinja2 templating
- Conditionally includes `project_name`, `project_language`, `project_description`
- Always includes `commit_guidelines`

**Override:** Set `system_prompt` in `[models]` section of your config.

---

## Default Input Template

```jinja2
############# Beginning of the diff #############
{{ diff }}
################ End of the diff ################
{% if bug or feat or docs or refact or custom_clue %}
Clues:
    {{ bug }}
    {{ feat }}
    {{ docs }}
    {{ refact }}
    {{ custom_clue }}
{% endif %}
```

**Features:**
- Wraps the diff with delimiters
- Conditionally appends clues if any are provided

---

## Default CommitClues Descriptions

When using CommitClues without descriptions, these defaults are used:

| Clue Flag | Default Description |
| :--- | :--- |
| `--bug` | "This commit focous on fixing a bug" |
| `--feat` | "This commit focous on a new feature" |
| `--docs` | "This commit focous on docs" |
| `--refact` | "This commit focous on refactoring" |

**Example:**
```bash
CommitCraft --bug
# Adds: "This commit focous on fixing a bug"

CommitCraft --feat-desc "Added OAuth"
# Adds: "This commit focous on a new feature: Added OAuth"
```

---

## Default Emoji Conventions

### Simple GitMoji (37 emojis)

```
⚡️ ; Improve performance.
🐛 ; Fix a bug.
🚑️ ; Critical hotfix.
✨ ; Introduce new features.
📝 ; Add or update documentation.
✅ ; Add, update, or pass tests.
🔒️ ; Fix security or privacy issues.
🔖 ; Release / Version tags.
🚨 ; Fix compiler / linter warnings.
⬇️ ; Downgrade dependencies.
⬆️ ; Upgrade dependencies.
♻️ ; Refactor code.
➕ ; Add a dependency.
➖ ; Remove a dependency.
🔧 ; Add or update configuration files.
🌐 ; Internationalization and localization.
✏️ ; Fix typos.
🚚 ; Move or rename resources (e.g.: files, paths, routes).
💥 ; Introduce breaking changes.
🍱 ; Add or update assets.
♿️ ; Improve accessibility.
💡 ; Add or update comments in source code.
🗃️ ; Perform database related changes.
🚸 ; Improve user experience / usability.
🏗️ ; Make architectural changes.
🤡 ; Mock things.
🥚 ; Add or update an easter egg.
🙈 ; Add or update a .gitignore file.
📸 ; Add or update snapshots.
⚗️ ; Perform experiments.
🏷️ ; Add or update types.
🥅 ; Catch errors.
🧐 ; Data exploration/inspection.
⚰️ ; Remove dead code.
🧪 ; Add a failing test.
👔 ; Add or update business logic.
🩺 ; Add or update healthcheck.
💸 ; Add sponsorships or money related infrastructure.

The title shall be formated as "{emoji} {title}"
```

### Full GitMoji (58 emojis)

Includes all emojis from "simple" plus:

```
🎨 ; Improve structure / format of the code.
🔥 ; Remove code or files.
🚀 ; Deploy stuff.
💄 ; Add or update the UI and style files.
🎉 ; Begin a project.
🔐 ; Add or update secrets.
🚧 ; Work in progress.
💚 ; Fix CI Build.
📌 ; Pin dependencies to specific versions.
👷 ; Add or update CI build system.
📈 ; Add or update analytics or track code.
🔨 ; Add or update development scripts.
💩 ; Write bad code that needs to be improved.
⏪️ ; Revert changes.
🔀 ; Merge branches.
📦️ ; Add or update compiled files or packages.
👽️ ; Update code due to external API changes.
📄 ; Add or update license.
💬 ; Add or update text and literals.
🔊 ; Add or update logs.
🔇 ; Remove logs.
👥 ; Add or update contributor(s).
📱 ; Work on responsive design.
🔍️ ; Improve SEO.
🌱 ; Add or update seed files.
🚩 ; Add, update, or remove feature flags.
💫 ; Add or update animations and transitions.
🗑️ ; Deprecate code that needs to be cleaned up.
🛂 ; Work on code related to authorization, roles and permissions.
🩹 ; Simple fix for a non-critical issue.
🧱 ; Infrastructure related changes.
🧑‍💻 ; Improve developer experience.
🧵 ; Add or update code related to multithreading or concurrency.
🦺 ; Add or update code related to validation.

The title shall be formated as "{emoji} {title}"
```

---

## Default Emoji Agent Prompt (for 2-step mode)

When using `emoji_steps = "2-step"`, a second AI call is made with this prompt:

```
Your mission is to recive a commit message and return an emoji based on the folowing guide.
Do not explain yourself, return only the single emoji.
```

Then the appropriate emoji convention (simple/full) is appended.

---

## Default Provider Models

When `model` is not specified, these defaults are used:

| Provider | Default Model | Notes |
| :--- | :--- | :--- |
| `ollama` | `qwen3` | Local instance |
| `ollama_cloud` | `qwen3-coder:480b-cloud` | Cloud models end in `-cloud` |
| `openai` | `gpt-3.5-turbo` | |
| `google` | `gemini-2.5-flash` | |
| `groq` | `qwen/qwen3-32b` | |
| `openai_compatible` | **None** (required) | Must specify model |

---

## Default Context Window (Ollama)

For local Ollama, if `num_ctx` is not specified, it's auto-calculated:

```python
def get_context_size(diff: str, system: str) -> int:
    input_len = len(system) + len(diff)
    num_ctx = int(min(max(input_len * 2.64, 1024), 128000))
    return num_ctx
```

**Formula:**
- Minimum: 1024 tokens
- Maximum: 128000 tokens
- Calculation: `(system_prompt_length + diff_length) * 2.64`

**Example:**
- Diff + system = 1000 characters → `num_ctx = 2640`
- Diff + system = 50000 characters → `num_ctx = 128000` (capped)

**Note:** Ollama Cloud does **not** use `num_ctx` (it uses the chat API which doesn't support this parameter).

---

## Default Emoji Configuration

| Setting | Default Value |
| :--- | :--- |
| `emoji_steps` | `"single"` |
| `emoji_convention` | `"simple"` |
| `emoji_model` | `None` |

---

## Default Configuration Locations

| Level | Linux/macOS | Windows |
| :--- | :--- | :--- |
| Global | `~/.config/commitcraft/` | `%APPDATA%\commitcraft\` |
| Project | `./.commitcraft/` | `.\.commitcraft\` |

---

## Default Environment Variable Names

### Standard Providers

| Provider | API Key Variable | Host Variable |
| :--- | :--- | :--- |
| Ollama (local) | - | `OLLAMA_HOST` |
| Ollama Cloud | `OLLAMA_API_KEY` | - |
| OpenAI | `OPENAI_API_KEY` | - |
| Google | `GOOGLE_API_KEY` | - |
| Groq | `GROQ_API_KEY` | - |
| OpenAI-compatible | `CUSTOM_API_KEY` | - |

### Named Providers

Pattern: `{NICKNAME}_API_KEY` (uppercase)

**Examples:**
- `[providers.remote_ollama]` → `REMOTE_OLLAMA_API_KEY`
- `[providers.deepseek]` → `DEEPSEEK_API_KEY`
- `[providers.litellm]` → `LITELLM_API_KEY`

---

## Default Ollama Host

```python
host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
```

**Default:** `http://localhost:11434`

---

## Default Behavior

| Feature | Default Behavior |
| :--- | :--- |
| Colors | Enabled (`FORCE_COLOR=1`) |
| Emoji generation | Enabled (`emoji_steps="single"`) |
| Emoji convention | GitMoji "simple" (37 emojis) |
| Debug mode | Disabled |
| Thinking tags | Hidden (not shown) |
| Git hook mode | Interactive prompts |
| Config format | TOML |
| Diff source | `git diff --staged -M` |

---

## Customizing Defaults

All defaults can be overridden via:

1. **Global config** (`~/.config/commitcraft/config.toml`)
2. **Project config** (`.commitcraft/config.toml`)
3. **CLI arguments**
4. **Environment variables**

See [Configuration Guide](config.md) for details.

---

## Source Code Reference

All defaults are defined in:
```
src/commitcraft/defaults.py
```

You can view the complete source to understand exact default values and templates.
