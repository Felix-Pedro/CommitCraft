"""
CommitCraft Core Module

This module provides the main functionality for generating commit messages
using Large Language Models (LLMs). It handles git diff retrieval, diff filtering,
prompt construction, and LLM interactions through various providers.
"""

import fnmatch
import logging
import subprocess
import uuid
from enum import Enum
from typing import Literal

from jinja2 import Template
from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator, model_validator

from .defaults import default
from .providers import LLMProviderError, get_provider

# Set up logging for security warnings
logger = logging.getLogger(__name__)

# The empty tree hash is a well-known git constant that represents an empty directory tree.
# It is used to generate a diff against "nothing" (e.g., for the initial commit or
# when diffing against a parentless HEAD during amend).
# This hash (4b825dc642cb6eb9a060e54bf8d69288fbee4904) is consistent across all git repositories.
GIT_EMPTY_TREE_HASH = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


# Custom exceptions to be raised when using openai_compatible provider.
class MissingModelError(ValueError):
    def __init__(self):
        self.message = "The model cannot be None for the 'openai_compatible' provider."
        super().__init__(self.message)


class MissingHostError(ValueError):
    def __init__(self):
        self.message = "The 'host' field is required and must be a valid URL when using the 'openai_compatible' provider."
        super().__init__(self.message)


def get_diff(amend: bool = False) -> str:
    """
    Retrieve the staged changes in the git repository.

    Executes 'git diff --staged -M' to get staged changes with move detection.
    If amend is True, it retrieves the changes that would be committed by 'git commit --amend',
    comparing the current index against HEAD's parent (or empty tree if HEAD is root).

    Args:
        amend: If True, generate diff for amending the last commit.

    Returns:
        The diff output as a string

    Raises:
        RuntimeError: If git command fails or git is not installed
    """
    try:
        if amend:
            # Check if HEAD exists
            try:
                subprocess.run(
                    ["git", "rev-parse", "--verify", "HEAD"],
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError:
                raise RuntimeError("Cannot amend: No HEAD commit found.")

            # Try to get HEAD^ (parent)
            try:
                subprocess.run(
                    ["git", "rev-parse", "--verify", "HEAD^"],
                    check=True,
                    capture_output=True,
                )
                # HEAD has a parent, diff against it
                cmd = ["git", "diff", "--cached", "HEAD^", "-M"]
            except subprocess.CalledProcessError:
                # HEAD is root commit, diff against empty tree
                cmd = ["git", "diff", "--cached", GIT_EMPTY_TREE_HASH, "-M"]
        else:
            cmd = ["git", "diff", "--staged", "-M"]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else "Unknown git error"
        raise RuntimeError(f"Git command failed: {error_msg}") from e
    except FileNotFoundError:
        raise RuntimeError(
            "Git is not installed or not in PATH. Please install git to use CommitCraft."
        ) from None


def matches_pattern(file_path: str, ignored_patterns: list[str]) -> bool:
    """
    Check if a file path matches any of the ignore patterns.

    Uses fnmatch for glob-style pattern matching (*, ?, [seq], [!seq]).

    Args:
        file_path: Path to check
        ignored_patterns: List of glob patterns to match against

    Returns:
        True if the file matches any pattern, False otherwise
    """
    return any(fnmatch.fnmatch(file_path, pattern) for pattern in ignored_patterns)


def get_filtered_diff(ignored_patterns: list[str], amend: bool = False) -> str:
    """
    Securely retrieve and filter git diff by listing files first, then requesting
    diffs only for allowed files. This approach prevents command injection via
    malicious filenames and handles edge cases (spaces, special chars) correctly.

    Security: Uses git's -z (NULL-separated) output to avoid ambiguity in filenames,
    and passes file paths as list arguments (not shell strings) to prevent injection.

    Args:
        ignored_patterns: List of glob patterns for files to exclude
        amend: If True, generate diff for amending the last commit

    Returns:
        Filtered diff output with excluded files removed

    Raises:
        RuntimeError: If git command fails or git is not installed
    """
    try:
        # Step 1: Determine the base comparison target
        if amend:
            # Check if HEAD exists
            try:
                subprocess.run(
                    ["git", "rev-parse", "--verify", "HEAD"],
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError:
                raise RuntimeError("Cannot amend: No HEAD commit found.")

            # Try to get HEAD^ (parent)
            try:
                subprocess.run(
                    ["git", "rev-parse", "--verify", "HEAD^"],
                    check=True,
                    capture_output=True,
                )
                # HEAD has a parent, use it as base
                base = "HEAD^"
            except subprocess.CalledProcessError:
                # HEAD is root commit, use empty tree
                base = GIT_EMPTY_TREE_HASH

            # Get list of staged files using NULL separator for safety
            files_cmd = ["git", "diff", "--cached", base, "--name-only", "-z"]
        else:
            # Get list of staged files using NULL separator for safety
            files_cmd = ["git", "diff", "--staged", "--name-only", "-z"]

        files_result = subprocess.run(
            files_cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        # Step 2: Split on NULL bytes and filter out empty strings
        all_files = [f for f in files_result.stdout.split("\0") if f]

        # Step 3: Filter files based on ignore patterns
        allowed_files = [
            f for f in all_files if not matches_pattern(f, ignored_patterns)
        ]

        # Step 4: If no files remain after filtering, return empty string
        if not allowed_files:
            return ""

        # Step 5: Request diff only for allowed files
        # Use -- to separate paths from options to prevent filename-as-option injection
        if amend:
            diff_cmd = ["git", "diff", "--cached", base, "-M", "--"] + allowed_files
        else:
            diff_cmd = ["git", "diff", "--staged", "-M", "--"] + allowed_files

        diff_result = subprocess.run(
            diff_cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        return diff_result.stdout

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else "Unknown git error"
        raise RuntimeError(f"Git command failed: {error_msg}") from e
    except FileNotFoundError:
        raise RuntimeError(
            "Git is not installed or not in PATH. Please install git to use CommitCraft."
        ) from None


def filter_diff(diff_output: str, ignored_patterns: list[str]) -> str:
    """
    DEPRECATED: Legacy function for backward compatibility.

    This function manually parses diff output which is vulnerable to filenames
    with special characters. Use get_filtered_diff() instead for new code.

    Filter git diff output to exclude files matching ignore patterns.

    Parses the diff output line-by-line, identifying file boundaries using
    'diff --git' markers, and excludes entire diff blocks for files that
    match any ignore pattern.

    Args:
        diff_output: Raw git diff output
        ignored_patterns: List of glob patterns for files to exclude

    Returns:
        Filtered diff output with excluded files removed
    """
    filtered_diff = []
    in_diff_block = False
    current_file = None

    for line in diff_output.splitlines():
        if line.startswith("diff --git"):
            in_diff_block = False
            # Extract the file path from the line, typically it comes after b/
            # Example: diff --git a/file.txt b/file.txt
            parts = line.split()
            if len(parts) > 3:
                current_file = parts[3][2:]  # Remove the 'b/' prefix
                in_diff_block = not matches_pattern(current_file, ignored_patterns)
            else:
                current_file = None

        if in_diff_block:
            filtered_diff.append(line)

    return "\n".join(filtered_diff)


class EmojiSteps(Enum):
    """If emoji should be performed in the same step as the message or in a separated one"""

    single = "single"
    false = False


class LModelOptions(BaseModel):
    """
    Configuration options for LLM models.

    Supports common parameters like temperature, max_tokens, and num_ctx (for Ollama).
    Extra parameters are allowed to support provider-specific options.
    """

    num_ctx: int | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    min_ctx: int | None = None
    max_ctx: int | None = None

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v: int | None) -> int | None:
        """Ensure max_tokens is a positive integer if provided."""
        if v is not None and v < 1:
            raise ValueError("max_tokens must be at least 1")
        return v

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float | None) -> float | None:
        """Ensure temperature is non-negative, typically between 0 and 2."""
        if v is not None and v < 0:
            raise ValueError("temperature must be non-negative")
        return v

    @field_validator("top_p")
    @classmethod
    def validate_top_p(cls, v: float | None) -> float | None:
        """Ensure top_p is between 0 and 1."""
        if v is not None and (v < 0 or v > 1):
            raise ValueError("top_p must be between 0 and 1")
        return v

    model_config = ConfigDict(extra="allow")  # Allows for extra arguments


class Provider(str, Enum):
    """The supported LLM Providers"""

    ollama = "ollama"
    ollama_cloud = "ollama_cloud"
    openai = "openai"
    google = "google"
    groq = "groq"
    anthropic = "anthropic"
    openai_compatible = "openai_compatible"


class LModel(BaseModel):
    """
    Model configuration containing provider, model name, system prompt, options, and host.

    Attributes:
        provider: The LLM provider (ollama, openai, google, groq, anthropic, openai_compatible)
        model: Model name/identifier (auto-set based on provider if not provided)
        system_prompt: Optional custom system prompt
        options: Optional model parameters (temperature, max_tokens, etc.)
        host: Optional host URL (required for openai_compatible, optional for ollama)
        api_key: Optional API key for authentication
        nickname: Optional user-defined name for this provider instance (from [providers] section)
    """

    provider: Provider = Provider.ollama
    model: str | None = (
        None  # Most providers have defaults, required for openai_compatible
    )
    system_prompt: str | None = None
    options: LModelOptions | None = None
    host: Literal["ollama_cloud"] | HttpUrl | None = (
        None  # required for openai_compatible
    )
    api_key: str | None = None
    nickname: str | None = None

    @model_validator(mode="after")
    def set_model_default(self):
        """Set default model name based on provider if not specified."""
        if not self.model:
            if self.provider == Provider.ollama:
                self.model = "qwen3"
            elif self.provider == Provider.ollama_cloud:
                self.model = "qwen3-coder:480b-cloud"
            elif self.provider == Provider.groq:
                self.model = "qwen/qwen3-32b"
            elif self.provider == Provider.google:
                self.model = "gemini-2.5-flash"
            elif self.provider == Provider.openai:
                self.model = "gpt-3.5-turbo"
        return self

    @model_validator(mode="after")
    def validate_provider_requirements(self):
        """Validate that required fields are set for specific providers."""
        # Enforce that 'model' is not None when using openai_compatible
        if self.provider == Provider.openai_compatible:
            if not self.model:
                raise MissingModelError()
        return self

    @model_validator(mode="after")
    def check_host_for_oai_custom(self):
        """Ensure host is provided for openai_compatible provider."""
        if self.provider == Provider.openai_compatible and not self.host:
            raise MissingHostError()
        return self


class EmojiConfig(BaseModel):
    """
    Configuration for emoji usage in commit messages.

    Attributes:
        emoji_steps: When to add emojis (single step or 2-step)
        emoji_convention: Which emoji convention to use (simple, full, or custom string)
        emoji_model: Optional separate model for emoji selection
    """

    emoji_steps: EmojiSteps = EmojiSteps.single
    emoji_convention: str = "simple"
    emoji_model: LModel | None = None


class CommitCraftInput(BaseModel):
    """
    Input data for commit message generation.

    Attributes:
        diff: Git diff output
        bug: Bug fix indicator (bool or description string)
        feat: Feature indicator (bool or description string)
        docs: Documentation indicator (bool or description string)
        refact: Refactoring indicator (bool or description string)
        custom_clue: Custom clue for the LLM (bool or description string)
    """

    diff: str
    bug: str | bool = False
    feat: str | bool = False
    docs: str | bool = False
    refact: str | bool = False
    custom_clue: str | bool = False


def clue_parser(input: CommitCraftInput) -> dict[str, str | bool]:
    """
    Parse commit clues from input and merge with default templates.

    Converts boolean clue flags to their descriptive text from defaults,
    and appends user-provided descriptions to the default templates.

    Args:
        input: CommitCraftInput with diff and optional clues

    Returns:
        Dictionary of parsed clues ready for template rendering
    """
    # Log warning if custom_clue is used (typically from COMMITCRAFT_CLUE env var)
    if input.custom_clue:
        logger.warning(
            "Using COMMITCRAFT_CLUE environment variable. "
            "Ensure this is set by a trusted source. "
            "Do not use CommitCraft in untrusted or unknown environments."
        )

    clues_and_input = {}
    for key, value in input.model_dump().items():
        if value is True:
            # Boolean flag - use default description
            clues_and_input[key] = default.get(key, key)
        elif value and value is not False:
            # User provided description - append to default template
            default_text = default.get(key, "")
            separator = ": " if default_text else ""
            clues_and_input[key] = f"{default_text}{separator}{value}"
    return clues_and_input


def commit_craft(
    input: CommitCraftInput,
    models: LModel = LModel(),
    context: dict[str, str] | None = None,
    emoji: EmojiConfig | None = None,
    debug_prompt: bool = False,
    dry_run: bool = False,
) -> str | dict:
    """
    Generate a commit message using an LLM based on staged git changes.

    This is the main entry point for CommitCraft. It processes the input diff,
    applies clues and context, constructs prompts using Jinja2 templates,
    and calls the appropriate LLM provider to generate a commit message.

    Args:
        input: CommitCraftInput containing the diff and optional clues
        models: LModel configuration specifying provider, model, and options
        context: Optional project context (name, language, description, guidelines)
        emoji: Optional emoji configuration for GitMoji support
        debug_prompt: If True, return the prompt instead of calling the LLM
        dry_run: If True, return token usage statistics without generating a message

    Returns:
        Generated commit message string, or dictionary of usage stats if dry_run=True

    Raises:
        LLMProviderError: If the provider fails to generate a response
        RuntimeError: If git operations fail
    """
    context = context or {}

    # Build system prompt from template
    system_prompt_template = models.system_prompt or default.get("system_prompt", "")
    system_prompt = Template(system_prompt_template).render(**context)

    # Generate high-entropy random separator for prompt injection protection
    # This creates a unique boundary like "DIFF_BOUNDARY_a1b2c3d4e5f6..."
    # An attacker cannot predict this UUID generated at runtime, preventing
    # delimiter escape attacks (similar to CSRF tokens or MIME boundaries)
    diff_separator = f"DIFF_BOUNDARY_{uuid.uuid4().hex}"

    # Build user prompt from diff and clues
    input_template = Template(default.get("input", ""))
    input_data = clue_parser(input)
    # Inject the random separator into the template context
    input_data["separator"] = diff_separator
    user_prompt = input_template.render(**input_data)

    # Add emoji guidelines to system prompt if enabled, or explicit no-emoji instruction if disabled
    if emoji and emoji.emoji_steps == EmojiSteps.single:
        if emoji.emoji_convention in ("simple", "full"):
            emoji_guide = default.get("emoji_guidelines", {}).get(
                emoji.emoji_convention, ""
            )
            system_prompt += f"\n\n{emoji_guide}"
        elif emoji.emoji_convention:
            system_prompt += f"\n\n{emoji.emoji_convention}"
    elif emoji and emoji.emoji_steps == EmojiSteps.false:
        # Explicitly instruct the model NOT to use emojis
        system_prompt += "\n\nIMPORTANT: Do NOT include any emojis in the commit message. Use plain text only."

    # Get provider instance
    try:
        model_options = models.options.model_dump() if models.options else {}
        provider = get_provider(
            provider_name=models.provider.value,
            model=models.model or "qwen3",  # Fallback to default model
            api_key=models.api_key,
            host=str(models.host) if models.host else None,
            options=model_options,
            nickname=models.nickname,
        )

        # Handle dry_run mode (with or without debug_prompt)
        if dry_run:
            usage_stats = provider.calculate_usage(system_prompt, user_prompt)

            # If debug_prompt is also enabled, add prompts to the output
            if debug_prompt:
                usage_stats["system_prompt"] = system_prompt
                usage_stats["user_prompt"] = user_prompt

            return usage_stats

        # Debug mode without dry_run: return prompts without calling LLM
        if debug_prompt:
            return f"system_prompt:\n{system_prompt}\n\nprompt:\n{user_prompt}"

        return provider.generate(system_prompt, user_prompt)
    except LLMProviderError as e:
        raise RuntimeError(f"Failed to generate commit message: {e}") from e
