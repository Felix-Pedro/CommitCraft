 # CommitCraft

CommitCraft is a tool designed to enhance your commit messages by leveraging Large Language Models (LLMs). It provides an intuitive interface that simplifies the process of generating better, more informative commit messages based on staged changes in your git repository.

## Features

- **Provider Agnostic**: Supports multiple LLM providers including Ollama, Ollama Cloud, Google, OpenAI, Groq, and any OpenAI-compatible endpoint.
- **Git Hook Integration**: Automatically generate commit messages via git hooks - works locally or globally across all repositories.
- **Interactive Configuration**: User-friendly wizard (`CommitCraft config`) to set up providers, models, and preferences.
- **Hierarchical Configuration**: Global configuration for user-wide defaults, project-specific overrides, and CLI arguments.
- **CommitClues**: Provide context clues (bug fixes, features, docs, refactoring) to help the AI generate more accurate messages.
- **Configurable Context Size**: Automatically adjusts the context size for optimal performance. (Ollama only)
- **Emoji Support**: Option to include emojis in your commit messages based on predefined conventions. Pre-configured with gitmoji specification.
- **Ignore Files**: Exclude specific files from diff analysis using patterns (like .gitignore).
- **User-Friendly CLI**: A command-line interface with colorful help messages and easy-to-use options.
- **Debug Mode**: Inspect prompts before sending to the LLM with `--debug-prompt`.
- **Customizable**: Allows to easily setup a personalized system prompt and contextual information for tuning your results to your project commit guidelines.

## Installation

You can install CommitCraft using `pipx` for a hassle-free experience:

```bash
pipx install commitcraft
```
Note : the default instalations is ollama only.

If you intent to use some provider other than ollama consider using one of the following:

```bash
pipx install 'commitcraft[openai]'
```

```bash
pipx install 'commitcraft[groq]'
```

```bash
pipx install 'commitcraft[google]'
```

```bash
pipx install 'commitcraft[all-providers]'
```

## Quick Start

### Interactive Configuration (Recommended)

The easiest way to get started is with the interactive configuration wizard:

```bash
CommitCraft config
```

This will guide you through:
- Choosing between **global** (user-wide) or **project** (repository-specific) configuration
- Selecting your LLM provider and model
- Setting up API keys (securely stored in `.env` files)
- Configuring emoji conventions and project context

### Git Hook Integration

Set up automatic commit message generation with git hooks:

```bash
# Install hook for current repository (interactive mode - default)
CommitCraft hook

# Install hook globally for all new repositories
CommitCraft hook --global

# Install in non-interactive mode (no prompts)
CommitCraft hook --no-interactive

# Remove the hook
CommitCraft hook --uninstall
```

#### Hook Modes

**Interactive Mode (Default):**
When you run `git commit`, the hook will prompt you:
1. **Commit type**: Bug fix, Feature, Documentation, Refactoring, or None
2. **Optional description**: Provide additional context for better commit messages

This allows you to use **CommitClues** directly within the hook workflow!

**Example workflow:**
```bash
git add .
git commit
# Hook prompts:
# > What type of commit is this?
# > [b] Bug fix
# > [f] Feature
# > [d] Documentation
# > [r] Refactoring
# > [n] None
# You enter: f
# > Describe the feature (optional):
# You enter: Added dark mode toggle
# CommitCraft generates message with --feat-desc "Added dark mode toggle"
```

**Non-Interactive Mode:**
Generates messages automatically without prompts. Useful for automated workflows or if you prefer always editing the message manually.

Once installed, the hook will automatically generate a commit message whenever you run `git commit`. The AI-generated message will be pre-filled in your editor for you to review and edit before finalizing.

**Hook Version Management:**

The git hook includes automatic version checking. If you update CommitCraft and your hook is outdated, you'll see a warning with tailored update instructions:

```
⚠️  CommitCraft hook is outdated (hook: 0.9.0, installed: 1.0.0)
   Update with: CommitCraft hook
```

The update command automatically matches your hook's configuration:
- **Local interactive hook**: `CommitCraft hook`
- **Local non-interactive hook**: `CommitCraft hook --no-interactive`
- **Global interactive hook**: `CommitCraft hook --global`
- **Global non-interactive hook**: `CommitCraft hook --global --no-interactive`

Simply run the suggested command to update your hook to the latest version.

## Configuration

CommitCraft uses a hierarchical configuration system that allows you to set global defaults and override them per-project:

1. **Global Configuration**: `~/.config/commitcraft/` (or platform-specific app directory)
2. **Project Configuration**: `./.commitcraft/` in your repository root
3. **CLI Arguments**: Override both configuration levels

Supported file types are TOML, YAML, and JSON. You can use either:
- A single `config.{toml|yaml|json}` file with all settings
- Separate files: `context.{ext}`, `models.{ext}`, `emoji.{ext}`

Alternatively, you can specify a configuration file path using the `--config-file` argument.

Your API keys should be stored in environment variables or in a `.env` file (CommitCraft will look for `CommitCraft.env` or `.env`).

## Usage

To use CommitCraft, simply run:

```bash
CommitCraft
```

If no arguments are provided, then the configuration files (if present) will be used to determine settings such as provider, model, and other options. If there are no configuration files, the tool will fall back to using default settings (ollama, gemma2).

The diff used by CommitCraft is the result of `git diff --staged -M` so you will need to add files you want to consider before using it.

You may pipe the output to other commands.

### Command-Line Arguments

#### Model Configuration
- `--provider`: Specifies the LLM provider (e.g., `ollama`, `ollama_cloud`, `google`, `openai`, `groq`, `openai_compatible`).
- `--model`: The name of the model to use.
- `--config-file`: Path to a configuration file.
- `--system-prompt`: A system prompt to guide the LLM.
- `--num-ctx`: Context size for the model.
- `--temperature`: Temperature setting for the model (0.0 to 1.0).
- `--max-tokens`: Maximum number of tokens for the model.
- `--host`: HTTP or HTTPS host for the provider (required for `openai_compatible`, optional for `ollama`).
- `--show-thinking`: Display model's thinking process if available (e.g., for DeepSeek).

#### CommitClues (Context Hints)
Give the AI more context about your changes:
- `--bug` / `--bug-desc "description"`: Indicate this commit fixes a bug
- `--feat` / `--feat-desc "description"`: Indicate this commit adds a feature
- `--docs` / `--docs-desc "description"`: Indicate this commit updates documentation
- `--refact` / `--refact-desc "description"`: Indicate this commit refactors code
- `--context-clue "custom hint"`: Provide a custom context clue

**Note:** If you're using the git hook in interactive mode (default), you'll be prompted for these clues automatically. Use these CLI flags when running CommitCraft manually.

#### Other Options
- `--ignore`: Files or patterns to exclude from the diff (comma-separated)
- `--debug-prompt`: Display the prompt without sending it to the LLM (useful for debugging)
- `--no-color` / `-p` / `--plain`: Disable colored output (for piping or scripting)

**Example:**
```bash
# Generate commit message for a bug fix with specific context
CommitCraft --bug-desc "Fixed null pointer in user authentication" --provider ollama --model qwen3

# Use custom provider with specific temperature
CommitCraft --provider openai --model gpt-4 --temperature 0.3 --max-tokens 500
```

### Example Configuration File

Here's an example configuration file in TOML format:

```toml
[context]
project_name = "MyProject"
project_language = "Python"
project_description = "A project to enhance commit messages."
commit_guidelines = "Ensure each commit is concise and describes the changes clearly."

[models]
provider = "ollama"
model = "qwen3"
system_prompt = "You are a helpful assistant for generating commit messages based on git diff."

[models.options]
num_ctx = 8192
temperature = 0.7
max_tokens = 1000

[emoji]
emoji_steps = "single"  # Options: "single", "2-step", or false
emoji_convention = "simple"  # Options: "simple", "full", or custom string

# Named provider profiles (optional - allows multiple provider configurations)
[providers.remote_ollama]
provider = "ollama"
model = "qwen3"
host = "https://my-ollama-server.example.com"

[providers.deepseek]
provider = "openai_compatible"
model = "deepseek-chat"
host = "https://api.deepseek.com"

[providers.deepseek.options]
temperature = 0.5
max_tokens = 800
```

#### Ignore Files

You can exclude files from the diff analysis by creating a `.commitcraft/.ignore` file with patterns (similar to `.gitignore`):

```
# .commitcraft/.ignore
*.lock
package-lock.json
poetry.lock
dist/*
*.min.js
```

Or use the `--ignore` flag:
```bash
CommitCraft --ignore "*.lock,dist/*"
```

You may want those settings to be 3 different files so for example the provider could be decided on a user-by-user basis, adding the models config file to the `.gitignore` file, but the emoji and context settings may be tracked by git.

### Environment Variables

For API keys and sensitive configuration, CommitCraft uses either a `.env` file in the execution directory or system-wide environment variables.

**Standard Providers:**
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

**Named Provider Profiles:**

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

### Provider-Specific Notes

#### Ollama Cloud

CommitCraft supports **Ollama Cloud** with the `ollama_cloud` provider. This connects to Ollama's cloud service at `https://ollama.com` using the chat API:

```bash
# Using CLI
CommitCraft --provider ollama_cloud --model qwen3-coder:480b-cloud

# Or in config file
[models]
provider = "ollama_cloud"
model = "qwen3-coder:480b-cloud"
```

**Requirements:**
- Get your API key from [ollama.com/settings/keys](https://ollama.com/settings/keys)
- Set the environment variable:
```sh
OLLAMA_API_KEY=your-ollama-cloud-key
```

**Note:** Unlike local Ollama, the cloud provider uses the chat API and automatically connects to `https://ollama.com`. The `--host` parameter is not needed for Ollama Cloud.

#### OpenAI-Compatible Providers

The `openai_compatible` provider allows you to use any OpenAI API-compatible service (e.g., DeepSeek, Together AI, LiteLLM, etc.):

```bash
CommitCraft --provider openai_compatible --model deepseek-chat --host https://api.deepseek.com
```

**Note:** In v1.0.0, `custom_openai_compatible` was renamed to `openai_compatible` for consistency.

## Privacy

CommitCraft itself does not log, record or send any information about your usage and project, or any other info. 

However, it is important to note that by using CommitCraft, you are agreeing to the terms of the providers you choose, as CommitCraft sends diffs and contextual information to their API. Unless you self-host the application, these providers may still collect your request history and metadata information. For more detailed information about how each provider handles your data, please review their respective privacy policies:

- [Ollama Cloud](https://ollama.com/cloud) 

    >Ollama Cloud FAQ:
    > 
    >**What data is logged in Ollama's cloud?**
    >
    > Ollama does not log prompt or response data.  
    >
    > (Accessed: December 7, 2025)


- [Groq](https://groq.com/privacy-policy/)
- [Google](https://ai.google.dev/gemini-api/terms)
- [OpenAI](https://openai.com/policies/privacy-policy/)
- [Anthropic](https://www.anthropic.com/legal/privacy)

## Pricing

CommitCraft is Free Software - free as in freedom and as in no price attached.

However, if you are not self-hosting your models, it's important to be aware of the pricing structure for the providers you use. Some providers offer free tiers, while others operate on usage-based pricing. For more detailed information about pricing options, please refer to the documentation provided by each provider:

- **Free Tier Available:**
  - [Ollama Cloud](https://ollama.com/pricing) - Free tier available
  - [Groq](https://groq.com/pricing/) - Generous free tier
  - [Google](https://ai.google.dev/pricing) - Free tier with quotas

- **Usage-Based Pricing:**
  - [OpenAI](https://openai.com/api/pricing/) - Pay per token
  - [Anthropic](https://console.anthropic.com/docs/en/about-claude/pricing) - Pay per token

- **Self-Hosted (Free):**
  - Ollama (local) - Completely free when self-hosted

## Troubleshooting

If for some reason a dependency is missing follow these steps:

1. Run the following command 

```sh
pipx inject commitcraft [dependency_name]
```

2. Report the problem to the issues page, also provide the command you used to install.


## License

This project is licensed under the AGPL 3.0 License - see the [LICENSE](https://github.com/Felix-Pedro/CommitCraft/blob/main/LICENSE) file for details.

---

Thank you for using CommitCraft! We hope this tool helps you craft better commit messages effortlessly.  
