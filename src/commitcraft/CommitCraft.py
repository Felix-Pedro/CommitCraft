import fnmatch
import os
import subprocess
from enum import Enum
from typing import List, Literal, Optional, Union

from jinja2 import Template
from pydantic import BaseModel, Extra, HttpUrl, conint, model_validator

from .defaults import default


# Custom exceptions to be raised when using openai_compatible provider.
class MissingModelError(ValueError):
    def __init__(self):
        self.message = "The model cannot be None for the 'openai_compatible' provider."
        super().__init__(self.message)


class MissingHostError(ValueError):
    def __init__(self):
        self.message = "The 'host' field is required and must be a valid URL when using the 'openai_compatible' provider."
        super().__init__(self.message)


def get_diff() -> str:
    """Retrieve the staged changes in the git repository."""
    diff = subprocess.run(
        ["git", "diff", "--staged", "-M"], capture_output=True, text=True
    )
    return diff.stdout


def matches_pattern(file_path: str, ignored_patterns: List[str]) -> bool:
    """Check if the file matches any of the ignore patterns using fnmatch"""
    for pattern in ignored_patterns:
        if fnmatch.fnmatch(file_path, pattern):
            return True
    return False


def filter_diff(diff_output: str, ignored_patterns: List):
    """Filters the diff output to exclude files listed in ignored_files."""
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


def get_context_size(diff: str, system: str) -> int:
    """Based on the git diff and system prompt estimate ollama context window needed"""
    input_len = len(system) + len(diff)
    num_ctx = int(min(max(input_len * 2.64, 1024), 128000))
    return num_ctx


class EmojiSteps(Enum):
    """If emoji should be performed in the same step as the message or in a separated one"""

    single = "single"
    step2 = "2-step"
    false = False


class LModelOptions(BaseModel):
    """The options for the LLM"""

    num_ctx: Optional[int] = None
    temperature: Optional[float] = None
    max_tokens: Optional[conint(ge=1)] = (
        None  # Ensure max_tokens is a positive integer if provided
    )

    class Config:
        extra = Extra.allow  # Allows for extra arguments


class Provider(str, Enum):
    """The supported LLM Providers"""

    ollama = "ollama"
    ollama_cloud = "ollama_cloud"
    openai = "openai"
    google = "google"
    groq = "groq"
    openai_compatible = "openai_compatible"


class LModel(BaseModel):
    """The model object containin the provider, model name, system prompt, option and host"""

    provider: Provider = Provider.ollama
    model: Optional[str] = (
        None  # Most providers have default, required for openai_compatible
    )
    system_prompt: Optional[str] = None
    options: Optional[LModelOptions] = None
    host: Optional[Union[Literal["ollama_cloud"], HttpUrl]] = (
        None  # required for openai_compatible
    )
    api_key: Optional[str] = None

    @model_validator(mode='after')
    def set_model_default(self):
        # If 'model' is not provided, set it based on 'provider'
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

    @model_validator(mode='after')
    def validate_provider_requirements(self):
        # Enforce that 'model' is not None when using openai_compatible
        if self.provider == Provider.openai_compatible:
            if not self.model:
                raise MissingModelError()
        return self

    @model_validator(mode='after')
    def check_host_for_oai_custom(self):
        if self.provider == Provider.openai_compatible and not self.host:
            raise MissingHostError()
        return self


class EmojiConfig(BaseModel):
    emoji_steps: EmojiSteps = EmojiSteps.single
    emoji_convention: str = "simple"
    emoji_model: Optional[LModel] = None


class CommitCraftInput(BaseModel):
    diff: str
    bug: str | bool = False
    feat: str | bool = False
    docs: str | bool = False
    refact: str | bool = False
    custom_clue: str | bool = False


def clue_parser(input: CommitCraftInput) -> dict[str, str | bool]:
    clues_and_input = {}
    for key, value in input.dict().items():
        if value is True:
            clues_and_input[key] = default.get(key, key)
        else:
            # if key == 'diff':
            #    clues_and_input['diff'] = value
            if value:
                clues_and_input[key] = (
                    default.get(key, "") + (": " if default.get(key) else "") + value
                )
            else:
                pass
    return clues_and_input


def commit_craft(
    input: CommitCraftInput,
    models: LModel = LModel(),  # Will support multiple models in 1.1.0 but for now only one
    context: dict[str, str] = {},
    emoji: Optional[EmojiConfig] = None,
    debug_prompt: bool = False,
) -> str:
    """CommitCraft generates a system message and requests a commit message based on staged changes"""

    system_prompt = (
        models.system_prompt
        if models.system_prompt
        else default.get("system_prompt", "")
    )
    system_prompt = Template(system_prompt)
    system_prompt = system_prompt.render(**context)

    input_wrapper = Template(default.get("input", ""))
    input_data = clue_parser(input)
    prompt = input_wrapper.render(**input_data)

    if emoji:
        if emoji.emoji_steps == EmojiSteps.single:
            if emoji.emoji_convention in ("simple", "full"):
                system_prompt += f"\n\n{default.get('emoji_guidelines', {}).get(emoji.emoji_convention, '')}"
            elif emoji.emoji_convention:
                system_prompt += f"\n\n{emoji.emoji_convention}"

    model = models
    model_options = model.options.dict() if model.options else {}
    if debug_prompt:
        return f"system_prompt:\n{system_prompt}\n\n prompt:\n{prompt}"
    match model.provider:
        case "ollama":
            import ollama

            # Ollama local instance initialization
            client_args = {}
            host_val = str(model.host) if model.host else os.getenv("OLLAMA_HOST")
            if host_val:
                client_args["host"] = host_val

            # API key support for authenticated Ollama instances
            ollama_api_key = (
                model.api_key if model.api_key else os.getenv("OLLAMA_API_KEY")
            )
            if ollama_api_key:
                client_args["headers"] = {"Authorization": f"Bearer {ollama_api_key}"}

            Ollama = ollama.Client(**client_args)

            if "num_ctx" in model_options.keys():
                if model_options["num_ctx"]:
                    return Ollama.generate(
                        model=model.model,
                        system=system_prompt,
                        prompt=prompt,
                        options=model_options,
                    )["response"]
                else:
                    model_options["num_ctx"] = get_context_size(prompt, system_prompt)
                    return Ollama.generate(
                        model=model.model,
                        system=system_prompt,
                        prompt=prompt,
                        options=model_options,
                    )["response"]
            else:
                model_options["num_ctx"] = get_context_size(prompt, system_prompt)
                return Ollama.generate(
                    model=model.model,
                    system=system_prompt,
                    prompt=prompt,
                    options=model_options,
                )["response"]

        case "ollama_cloud":
            import ollama

            # Ollama Cloud configuration per https://docs.ollama.com/cloud#python
            client_args = {
                "host": "https://ollama.com"
            }

            # Cloud requires API key authentication
            ollama_api_key = (
                model.api_key if model.api_key else os.getenv("OLLAMA_API_KEY")
            )
            if ollama_api_key:
                client_args["headers"] = {"Authorization": f"Bearer {ollama_api_key}"}

            Ollama = ollama.Client(**client_args)

            # Ollama Cloud uses chat API, not generate API
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]

            # Filter options for chat API (cloud doesn't use num_ctx)
            chat_options = {k: v for k, v in model_options.items() if k != "num_ctx"}

            response = Ollama.chat(
                model=model.model,
                messages=messages,
                options=chat_options if chat_options else None,
            )
            return response["message"]["content"]

        case "groq":
            from groq import Groq

            client = Groq(
                api_key=model.api_key if model.api_key else os.getenv("GROQ_API_KEY")
            )
            groq_configs = ("top_p", "temperature", "max_tokens")
            groq_options = {
                config: model_options.get(config) if model_options.get(config) else None
                for config in (set(tuple(model_options.keys())) & set(groq_configs))
            }
            return (
                client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    model=model.model,
                    stream=False,
                    **groq_options,
                )
                .choices[0]
                .message.content
            )

        case "google":
            from google import genai
            from google.genai import types

            client = genai.Client(
                api_key=model.api_key if model.api_key else os.getenv("GOOGLE_API_KEY")
            )

            google_config = {}
            if system_prompt:
                google_config["system_instruction"] = system_prompt

            if model_options:
                if model_options.get("temperature"):
                    google_config["temperature"] = model_options.get("temperature")
                if model_options.get("max_tokens"):
                    google_config["max_output_tokens"] = model_options.get("max_tokens")
                if model_options.get("top_p"):
                    google_config["top_p"] = model_options.get("top_p")

            response = client.models.generate_content(
                model=model.model,
                contents=prompt,
                config=types.GenerateContentConfig(**google_config),
            )
            return response.text

        case "openai":
            from openai import OpenAI

            client = OpenAI(
                api_key=model.api_key if model.api_key else os.getenv("OPENAI_API_KEY")
            )
            openai_configs = ("top_p", "temperature", "max_tokens")
            openai_options = {
                config: model_options.get(config) if model_options.get(config) else None
                for config in (set(tuple(model_options.keys())) & set(openai_configs))
            }
            return (
                client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    model=model.model,
                    stream=False,
                    **openai_options,
                )
                .choices[0]
                .message.content
            )

        case "openai_compatible":
            from openai import OpenAI

            client = OpenAI(
                api_key=model.api_key
                if model.api_key
                else os.getenv("CUSTOM_API_KEY", default="nokey"),
                base_url=str(model.host),
            )
            openai_configs = ("top_p", "temperature", "max_tokens")
            openai_options = {
                config: model_options.get(config) if model_options.get(config) else None
                for config in (set(tuple(model_options.keys())) & set(openai_configs))
            }
            return (
                client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    model=model.model,
                    stream=False,
                    **openai_options,
                )
                .choices[0]
                .message.content
            )

        case _:
            raise NotImplementedError("provider not found")
