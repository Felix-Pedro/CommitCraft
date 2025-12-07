# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to (or tries to) [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [unreleased]

### Added

- **Ollama Cloud**: Added native support for `ollama_cloud` provider using the official chat API with proper authentication to `https://ollama.com`.
- **Multi-Provider Management**: Enhanced interactive config to add, edit, and delete additional provider profiles.
- **Improved UI**: Model selection now supports choosing by index number, and API key inputs show visual feedback (`***`) using `rich`.
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

[unreleased]: https://github.com/Felix-Pedro/CommitCraft/compare/latest...HEAD
[0.1.1]: https://github.com/Felix-Pedro/CommitCraft/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Felix-Pedro/CommitCraft/releases/tag/v0.1.0
