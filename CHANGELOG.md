# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to (or tries to) [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [unreleased]

### Added

- **Ollama Cloud**: Added native support for `ollama_cloud` provider.
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
- Forced color support by default to fix color detection issues in zsh and other shells.

### Changed

- **BREAKING CHANGE**: Renamed `custom_openai_compatible` provider to `openai_compatible`.
- Refactored CLI to use typer for more flexibility and better help messages
- Upgraded Google GenAI dependencies to v0.2.0.
- Updated default model versions for supported providers.
- Changed `rich_markup_mode` from "markdown" to "rich" for proper color tag support.

### Fixed

- Fixed color output not appearing in zsh terminal by forcing color support by default.
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
