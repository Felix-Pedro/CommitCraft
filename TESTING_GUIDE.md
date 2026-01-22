# Testing Guide

This document provides instructions for setting up and running the CommitCraft test suite across multiple Python versions.

## Prerequisites

1.  **uv**: The primary tool for managing Python versions, virtual environments, and dependencies.
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

## Running Tests

CommitCraft uses **Nox** to automate testing across different Python environments. We use **uv** as the backend for Nox to speed up environment creation and package installation.

### 1. Install Dependencies

Sync the project dependencies (including development groups):

```bash
uv sync
```

### 2. Run All Unit Tests (Recommended)

To run the full test suite across all supported Python versions (3.10, 3.11, 3.12, 3.13, 3.14) plus linting, formatting, and type checking:

```bash
uv run nox
```

Nox will automatically exclude live integration tests by default, ensuring the suite is fast and cost-free.

### 3. Live Integration Tests

CommitCraft includes integration tests that make real API calls to verify provider compatibility. These are marked as `live` and are **skipped by default** to avoid unexpected costs.

**To run live tests:**
1.  Set the required API keys in your environment:
    ```bash
    export OPENAI_API_KEY="sk-..."
    export ANTHROPIC_API_KEY="sk-ant-..."
    export GROQ_API_KEY="gsk-..."
    export GOOGLE_API_KEY="AI..."
    ```
2.  Run pytest with the `live` marker (use `-rs` to see skip reasons):
    ```bash
    uv run pytest -m live -rs
    ```

*Note: Live tests use the cheapest available models (e.g., `gpt-4o-mini`, `claude-3-haiku`, `gemini-1.5-flash`) with minimal prompts to keep costs negligible.*

### 4. Run Specific Sessions

You can run specific parts of the test suite:

**Run tests only on Python 3.13:**
```bash
uv run nox -s tests-3.13
```

**Run linting only:**
```bash
uv run nox -s lint
```

**Check formatting only:**
```bash
uv run nox -s format
```

**Run type checking only:**
```bash
uv run nox -s type_check
```

## Documentation Testing

CommitCraft uses **MkDocs** with the **Material** theme to generate its documentation. You should verify that your changes don't break the documentation build and that they render correctly.

### 1. Preview Docs Locally

To start a local development server with live-reloading:

```bash
uv run mkdocs serve
```

Once started, you can view the documentation at `http://127.0.0.1:8000`.

### 2. Verify Build

To ensure the documentation builds successfully without errors:

```bash
uv run mkdocs build
```

The generated files will be placed in the `site/` directory.

## Troubleshooting

If you encounter issues with Python versions not being found:

1.  Ensure `uv` is in your PATH.
2.  You can manually install Python versions with `uv` if needed:
    ```bash
    uv python install 3.10 3.11 3.12 3.13 3.14
    ```

## Test Structure

-   `tests/test_cli.py`: Tests for the CLI entry point and arguments.
-   `tests/test_config.py`: Tests for URL validation and model fetching helpers.
-   `tests/test_config_utils.py`: Tests for configuration merging and file loading.
-   `tests/test_core_logic.py`: Tests for core CommitCraft logic (clue parsing, model defaults).
-   `tests/test_providers_mock.py`: **New** Unit tests for all LLM providers using mocks (cost-free).
-   `tests/test_providers_live.py`: **New** Live integration tests for real API verification (requires keys).
-   `tests/test_google_provider.py`: Native token counting tests for Google Gemini.
-   `tests/test_utils.py`: Tests for utility functions like diff filtering.