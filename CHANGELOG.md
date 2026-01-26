# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to (or tries to) [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [unreleased]

### Changed

- **Documentation - 2-Step Emoji Clarification**: Updated documentation to clearly indicate that the 2-step emoji system (`emoji_steps = "2-step"`) is planned for version 1.2 but not yet fully implemented. Currently, only `"single"` (default) and `false` emoji modes are functional. The 2-step mode is defined in code but the implementation logic is pending.
- **Package Manager Migration**: Migrated from Poetry to uv for faster dependency management and simpler tooling. Development commands now use `uv sync` and `uv run` instead of `poetry install` and `poetry run`. Both `uv tool install` and `pipx install` are supported for end-user installation.
- **All Providers by Default**: The default installation now includes all providers (Ollama, OpenAI, Groq, Google, Anthropic) out of the box.
- **Provider System Refactored**: Internal provider implementation now uses a registry pattern with abstract base classes (`LLMProvider`) for better maintainability and extensibility. This is a non-breaking internal refactor that makes it easier to add new LLM providers. All existing provider names, CLI arguments, and configuration options work identically. Includes improved API key handling with explicit `requires_api_key` declarations, better error messages, support for local/unauthenticated services, and enhanced token counting with tiktoken integration and graceful fallbacks.

### Added

- **COMMITCRAFT_CLUE Environment Variable**: Added `COMMITCRAFT_CLUE` environment variable to provide custom CommitClues (personalized context hints) via environment variables. This allows setting a default custom clue that will be used when `--context-clue` is not explicitly provided on the command line. Useful for CI/CD pipelines or when you want to set a persistent clue in your `.env` file without using CLI flags every time. Example: `COMMITCRAFT_CLUE="Performance optimization"`.
- **Environment Variables Command**: Added `CommitCraft envvars` command to display a comprehensive, categorized table of all supported environment variables with descriptions and examples. Categories include API Keys, Provider Configuration, Model Options, Behavior & Features, Output & Display, and Git Hook Settings. The main help message now includes a hint to run this command for the full list instead of showing a truncated list inline.
- **COMMITCRAFT_CLUE_PROMPT Environment Variable**: Added `COMMITCRAFT_CLUE_PROMPT` environment variable to control CommitClue prompts in git hooks, overriding the hook's installed mode. Set `COMMITCRAFT_CLUE_PROMPT=1` or `COMMITCRAFT_CLUE_PROMPT=true` to always prompt for CommitClues (enables interactive mode), `COMMITCRAFT_CLUE_PROMPT=0` to never prompt (forces non-interactive mode), or leave unset to use the hook's default behavior as defined during installation. This provides runtime control over hook interactivity without reinstalling.
- **Combined Debug and Dry-Run Modes**: The `--debug-prompt` and `--dry-run` flags can now be used together. When combined, the output includes both token usage statistics and the full system/user prompts, making it easier to debug prompt construction while reviewing token consumption. Previously, these flags were mutually exclusive. Use the `--compact` flag to show prompts only in the table (truncated) without full output below, which is useful for demos and presentations.
- **No-Emoji Flag**: Added `--no-emoji` CLI flag and `COMMITCRAFT_NO_EMOJI` environment variable to disable emoji in commit messages for a single invocation, overriding configuration file settings. When emojis are disabled, the model receives an explicit instruction to NOT use any emojis in the output, ensuring plain text commit messages.
- **Automatic Update Checking**: CommitCraft now automatically checks for new versions weekly (opt-out by default). Update notifications are displayed after successful commit message generation and when installing/updating git hooks. The check uses PyPI's public API with a 2-second timeout and caches results to avoid excessive network calls. Users are notified about available updates with clear instructions for updating via `uv tool upgrade commitcraft` or `pipx upgrade commitcraft`. Checking can be disabled by adding `[updates] check_enabled = false` to your config file, and the check interval is configurable (default: 7 days). This helps ensure users receive important security patches and new features.

- **Two-Step Confirmation Mode**: Added `--confirm` flag and `COMMITCRAFT_CONFIRM` environment variable to enable a two-step process: (1) show dry-run statistics and configuration preview, then (2) prompt for user confirmation before generating the commit message. This is particularly useful when using git hooks to review token usage and settings before making API calls. Can be enabled via CLI flag or environment variable, and is supported in both interactive and non-interactive hook modes via `CommitCraft hook --confirm`.
- **Anthropic Provider**: Added native support for Anthropic's Claude models with automatic token counting via Anthropic's `count_tokens()` API. Includes intelligent Claude model detection when using OpenAI-compatible routers (LiteLLM, OpenRouter) - automatically uses native Anthropic token counting for accurate estimates. Interactive config wizard dynamically fetches available models from Anthropic API. Supports all Claude models including Claude Opus 4.5, Haiku 4.5, and Sonnet 4.5. Requires `ANTHROPIC_API_KEY` environment variable.
- **Enhanced Dry Run Output**: Dry run mode (`--dry-run`) now displays provider name and host URL for better transparency. When using named provider profiles from `[providers]` config, shows the user-defined nickname (e.g., "litellm") instead of the generic provider type (e.g., "openai_compatible").
- **Dry Run Mode**: Added `--dry-run` flag to the CLI which calculates and displays token usage statistics (input tokens, model name, provider, host, context utilization) without making a request to the LLM or generating a commit message. Supports both Rich table output and JSON output (with `--plain`).
- **Amend Mode**: Added `--amend` flag to generate commit messages for `git commit --amend`. It intelligently calculates the diff by comparing the current index against the parent of HEAD (or the empty tree if amending a root commit).
- **Default Ignore Patterns**: Lock files, minified assets, source maps, and other noisy files are now ignored by default when generating commit messages. Default patterns include `*.lock`, `package-lock.json`, `pnpm-lock.yaml`, `*.min.js`, `*.min.css`, `*.map`, `*.snap`, `*.pb.go`, `*.pb.js`, `*_generated.*`, `*.d.ts`, and `*.svg`.
- **Generate Ignore File**: Added `CommitCraft config --generate-ignore` (or `-i`) to quickly create a `.commitcraft/.ignore` file with default patterns for customization. The interactive config wizard also prompts to generate this file.
- **Loading Bits**: Added a few more loading phrases to entertain while generating the message
- **Hook Skip Option**: Added `COMMITCRAFT_SKIP=1` environment variable to skip CommitCraft for a single commit. Use `COMMITCRAFT_SKIP=1 git commit` to bypass the hook temporarily.
- **Unhook Command**: Added `CommitCraft unhook` command as a more discoverable alias for `CommitCraft hook --uninstall`. Supports `--global` / `-g` flag to remove global hooks.
- **Auto-Skip on `-m` Flag**: Hook now automatically skips when using `git commit -m "message"` since the user has already provided their own commit message.
- **Interactive Skip Option**: Added `[s] Skip (write message manually)` option to the interactive hook menu, allowing users to bypass AI generation for a single commit.
- **Configuration Helper Module**: Added `config_resolver.py` with dedicated functions for resolving provider configurations, named profiles, and applying CLI overrides, improving code organization and testability.

### Fixed

- **Security - Command Injection Prevention**: Hardened diff filtering to prevent potential command injection vulnerabilities from malicious filenames containing special characters (spaces, newlines, quotes). The new implementation uses git's `-z` (NULL-separated) output for unambiguous file path parsing and passes paths as list arguments instead of shell strings. Introduced `get_filtered_diff()` function that uses a secure "list-then-diff" approach: (1) retrieves file list with `git diff --name-only -z`, (2) filters against ignore patterns, (3) requests diff only for approved files using `--` separator. The legacy `filter_diff()` function is retained for backward compatibility but marked as deprecated.
- **Empty Diff Validation**: Added validation to prevent wasted API calls when there are no staged changes or all changes are filtered out by ignore patterns. Now displays a helpful message: "No staged changes to analyze. Either there are no staged changes, or all files are ignored by the filter patterns."
- **Pydantic v2 Compatibility**: Updated `model_dump()` and `ConfigDict` usage to address deprecation warnings when running with Pydantic v2.
- **Git Error Handling**: Added comprehensive error handling for `get_diff()` function. Now properly catches and reports errors when git is not installed or when git commands fail (e.g., not in a git repository).
- **Type Hints Modernization**: Updated all type hints to use modern Python 3.10+ syntax (`str | None` instead of `Optional[str]`, `dict[str, str]` instead of `Dict[str, str]`), improving consistency and readability.
- **Dead Code Removal**: Removed commented-out code blocks in `clue_parser()` and other functions, improving code cleanliness.

### Improved

- **Comprehensive Docstrings**: Added detailed docstrings to all core functions including parameter descriptions, return types, raised exceptions, and usage examples. Functions like `get_diff()`, `filter_diff()`, `matches_pattern()`, `clue_parser()`, and `commit_craft()` now have complete documentation.
- **Pydantic Validation**: Enhanced `LModelOptions` with explicit field validators (e.g., ensuring `max_tokens` is positive), providing better error messages and input validation.
- **Test Coverage**: Updated unit tests to cover new error handling paths, including git command failures and missing git installations. Tests now verify that proper exceptions are raised with appropriate error messages.
- **Error Messages**: Improved error messages throughout the codebase to be more descriptive and actionable, helping users quickly diagnose configuration and runtime issues.

### Developer Experience

- **Provider Registry Pattern**: Introduced `providers.py` module with `LLMProvider` abstract base class and provider-specific implementations (`OllamaProvider`, `GoogleProvider`, `OpenAIProvider`, etc.). New providers can be added by implementing the base class and registering in `PROVIDER_REGISTRY`.
- **Simplified Core Logic**: Reduced `commit_craft()` function from ~220 lines to ~60 lines by extracting provider-specific logic into dedicated classes, significantly improving maintainability.
- **Consistent Error Handling**: Established consistent error handling patterns using custom exceptions (`LLMProviderError`, `APIKeyMissingError`) that propagate meaningful error messages to users.

---

## [1.0.0] - 2025-12-07

### Added

- **Use Global Model Settings**: Added option in interactive config to skip project-specific model configuration and use global settings instead. When configuring a project-level config, users are now prompted "Configure project-specific model settings? (No = use global settings)" allowing projects to inherit model settings from the global configuration.

- **Ollama Cloud**: Added native support for `ollama_cloud` provider using the official chat API with proper authentication to `https://ollama.com`.
- **Multi-Provider Management**: Enhanced interactive config to add, edit, and delete additional provider profiles.
- **Debug Mode**: Added `--debug-prompt` option to inspect prompts without sending requests to the model.
- Named provider environment variables now use `NICKNAME_API_KEY` format (e.g., `LITELLM_API_KEY`) instead of `PROVIDER_NICKNAME_API_KEY`.
- Introducing : **CommitClues**, a simple way to help your model get a little bit more specific context.
- Ignore files diff for your CommitCraft request using --ignore or .commitcraft/.ignore file
- New Config option to allow changing configs on starting a new one
- Add merging configurations
- **Colorful Help Messages**: Added Rich markup to help text for colorful, easy-to-read CLI help output.
- **Plain Output Mode**: Added `--no-color` / `-p` / `--plain` flags to disable colored output for piping/scripting.
- **Forced Color Support**: Colors are now enabled by default with `FORCE_COLOR=1` to ensure consistent output across different shells.
- **Fun Loading Messages**: Added randomized funny programming and AI jokes to the commit generation loading spinner. Messages rotate every 3 seconds during longer operations.
- **Git Hook Integration**: Implemented `CommitCraft hook` command to set up automatic commit message generation via git hooks. Supports both local repository hooks and global git templates.
- **Interactive Git Hook Mode**: Git hooks now prompt for commit type (bug/feature/docs/refactor) and optional descriptions, allowing CommitClues to be used directly in the hook workflow. Interactive mode is enabled by default; use `--no-interactive` flag to disable prompts.
- **Hook Version Checking**: Git hooks now automatically check if they're outdated and display upgrade instructions when CommitCraft is updated.
- **Version Flag**: Added `--version` / `-v` flag to display the installed CommitCraft version.
- **Documentation - Emoji Configuration**: Added comprehensive emoji configuration guide to `docs/config.md` explaining `emoji_steps` (single/2-step/false) and `emoji_convention` (simple/full/custom) with complete GitMoji emoji lists for both simple (37 emojis) and full (58 emojis) conventions.
- **Documentation - Default Models**: Added default model versions table and provider-specific options support matrix to `docs/cli.md` showing which options work with which providers.
- **Documentation - CommitClues Guide**: Added complete CommitClues usage guide to `docs/recipes.md` with examples of boolean flags, descriptive flags, combining clues, and integration with git hooks.
- **Documentation - Context Variables**: Added context variables and Jinja2 templating documentation to `docs/config.md` explaining how to use `{{ project_name }}`, `{{ project_language }}`, `{{ project_description }}`, and `{{ commit_guidelines }}` in system prompts.
- **Documentation - CLI Context Options**: Added default context options table to `docs/cli.md` documenting `--project-name`, `--project-language`, `--project-description`, and `--commit-guide` flags.
- **Documentation - Named Provider Profiles**: Added extensive named provider profiles documentation to `docs/config.md` with real-world examples for multiple Ollama instances, multiple OpenAI-compatible services, and mixed provider use cases.
- **Documentation - Configuration Precedence**: Added detailed configuration merging behavior documentation to `docs/config.md` explaining the hierarchy and how settings are merged between CLI args, project config, global config, and defaults.
- **Documentation - Environment Variables**: Added complete environment variables reference to `docs/config.md` listing all `COMMITCRAFT_*` variables for configuration and provider API keys.
- **Documentation - Ollama Cloud Setup**: Added step-by-step Ollama Cloud setup guide to `docs/config.md` with API key instructions, configuration examples, available models, and troubleshooting.
- **Documentation - Thinking Tags**: Added model thinking process documentation to `docs/cli.md` explaining the `--show-thinking` flag for debugging with reasoning models like DeepSeek R1 and QwQ.
- **Documentation - Diff Filtering**: Expanded diff filtering examples in `docs/config.md` with fnmatch pattern syntax table and language-specific ignore examples for Python, JavaScript, Rust, Go, and general projects.
- **Documentation - Extended Troubleshooting**: Added 15+ new troubleshooting scenarios to `docs/troubleshooting.md` including missing model/host errors, token limit issues, hook permission problems, GUI client issues, configuration errors, and environment variable problems.
- **Documentation - Migration Guide**: Created comprehensive v0.x to v1.0.0 migration guide at `docs/migration.md` covering breaking changes, new features, step-by-step migration instructions, and rollback procedures.
- **Documentation - Complete API Reference**: Rewrote `docs/reference.md` with full Python API documentation including all functions (`commit_craft`, `get_diff`, `filter_diff`, `clue_parser`), data models (`CommitCraftInput`, `LModel`, `LModelOptions`, `Provider`, `EmojiConfig`, `EmojiSteps`), exceptions, type hints, and complete automation script example.
- **Documentation - Defaults Reference**: Created `docs/defaults.md` documenting all default values including commit guidelines, system prompt template, input template, CommitClues descriptions, emoji conventions (simple/full), default models per provider, context window calculation, and default environment variables.

### Changed

- **BREAKING CHANGE**: Renamed `custom_openai_compatible` provider to `openai_compatible`.
- **Ollama Cloud Default Model**: Changed default model from `qwen3` to `qwen3-coder:480b-cloud` to match Ollama Cloud's actual model naming convention (all cloud models end with `-cloud` suffix).
- Refactored CLI to use typer for more flexibility and better help messages
- Upgraded Google GenAI dependencies to v0.2.0.
- Updated default model versions for supported providers.
- Changed `rich_markup_mode` from "markdown" to "rich" for proper color tag support.

### Fixed

- Fixed help messages not respecting `NO_COLOR` environment variable.
- **Click 8.3+ Compatibility**: Pinned `click` to versions `>=8.1.0,<8.2.0` to avoid incompatibility with Click 8.3.0+'s stricter validation of boolean flags. Click 8.3+ introduced breaking changes that caused `TypeError: Secondary flag is not valid for non-boolean flag` errors. All boolean CLI options now explicitly specify `is_flag=True` for forward compatibility.

### Removed

- BREAKING CHANGES: extra model options are not named arguments anymore

## [0.1.1] -2024-10-23

### Fixed

- Fixed f-string error for earlier versions of python.

## [0.1.0] - 2024-10-21

### Added

- Custom system prompt.
- Custom OpenAI Compatible Provider Support.
- OpenAI Support.
- Google Support
- Groq Support.
- Promptfoo testing.
- Ollama Support.
- GitMoji prompt.
- Default system prompt.

[unreleased]: https://github.com/Felix-Pedro/CommitCraft/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/Felix-Pedro/CommitCraft/compare/v0.1.1...v1.0.0
[0.1.1]: https://github.com/Felix-Pedro/CommitCraft/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Felix-Pedro/CommitCraft/releases/tag/v0.1.0
