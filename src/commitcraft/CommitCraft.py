import subprocess
import os
import fnmatch
from .defaults import default
from enum import Enum
from typing import List
from pydantic import BaseModel, conint, Extra, root_validator, HttpUrl
from typing import Optional
from jinja2 import Template

# Custom exceptions to be raised when using custom_openai_compatible provider.
class MissingModelError(ValueError):
    def __init__(self):
        self.message = "The model cannot be None for the 'custom_openai_compatible' provider."
        super().__init__(self.message)

class MissingHostError(ValueError):
    def __init__(self):
        self.message = "The 'host' field is required and must be a valid URL when using the 'custom_openai_compatible' provider."
        super().__init__(self.message)

def get_diff() -> str:
    """Retrieve the staged changes in the git repository."""
    diff = subprocess.run(['git', 'diff', '--staged', '-M'], capture_output=True, text=True)
    return diff.stdout

def matches_pattern(file_path : str, ignored_patterns : List[str]) -> bool:
    """Check if the file matches any of the ignore patterns using fnmatch"""
    for pattern in ignored_patterns:
        if fnmatch.fnmatch(file_path, pattern):
            return True
    return False

def filter_diff(diff_output : str, ignored_patterns : List):
    """Filters the diff output to exclude files listed in ignored_files."""
    filtered_diff = []
    in_diff_block = False
    current_file = None

    for line in diff_output.splitlines():
        if line.startswith('diff --git'):
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

    return '\n'.join(filtered_diff)

def get_context_size(diff : str, system : str) -> int:
    """Based on the git diff and system prompt estimate ollama context window needed"""
    input_len = len(system) + len(diff)
    num_ctx = int(min(max(input_len*2.64, 1024), 128000))
    return num_ctx


class EmojiSteps(Enum):
    """If emoji should be performed in the same step as the message or in a separated one"""
    single = 'single'
    step2 = '2-step'
    false = False


class LModelOptions(BaseModel):
    """The options for the LLM"""
    num_ctx: Optional[int] = None
    temperature: Optional[float] = None
    max_tokens: Optional[conint(ge=1)] = None  # Ensure max_tokens is a positive integer if provided

    class Config:
        extra = Extra.allow # Allows for extra arguments

class Provider(str, Enum):
    """The supported LLM Providers"""
    ollama = 'ollama'
    openai = 'openai'
    google = 'google'
    groq = 'groq'
    oai_custom = 'custom_openai_compatible'

class LModel(BaseModel):
    """The model object containin the provider, model name, system prompt, option and host"""
    provider: Provider = Provider.ollama
    model: Optional[str] = None # Most providers have default, required for custom_openai_compatible
    system_prompt: Optional[str] = None
    options: Optional[LModelOptions] = None
    host: Optional[HttpUrl] = None  # required for custom_openai_compatible

    @root_validator(pre=True)
    def set_model_default(cls, values):
        # If 'model' is not provided, set it based on 'provider'
        provider = values.get('provider')
        if 'model' not in values or values['model'] is None:
            if provider == Provider.ollama:
                values['model'] = 'gemma2'
            if provider == Provider.groq:
                values['model'] = 'llama-3.1-70b-versatile'
            elif provider == Provider.google:
                values['model'] = 'gemini-1.5-pro'
            elif provider == Provider.openai:
                values['model'] = 'gpt-3.5-turbo'
        return values

        @root_validator(pre=True)
        def validate_provider_requirements(cls, values):
            provider = values.get('provider')

            # Enforce that 'model' is not None when using custom_openai_compatible
            if provider == Provider.oai_custom:
                if not values.get('model'):
                    raise MissingModelError()

            return values

        @root_validator(pre=True)
        def check_host_for_oai_custom(cls, host, values):
            provider = values.get('provider')
            if provider == Provider.oai_custom and not host:
                raise MissingHostError()

            return host

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

def clue_parser(input : CommitCraftInput) -> dict[str, str | bool]:
    clues_and_input = {}
    for key, value in input.dict().items():
        if value is True:
            clues_and_input[key] = default.get(key, key)
        else:
            #if key == 'diff':
            #    clues_and_input['diff'] = value
            if value:
                clues_and_input[key] = default.get(key, '') + (':' if default.get(key) else '') + value
            else:
                pass
    return clues_and_input

def commit_craft(
    input : CommitCraftInput,
    models : LModel = LModel(), # Will support multiple models in 1.1.0 but for now only one
    context : dict[str, str] = {},
    emoji : Optional[EmojiConfig] = None,
    debug_prompt: bool = False

) -> str:
    """CommitCraft generates a system message and requests a commit message based on staged changes """

    system_prompt = models.system_prompt if models.system_prompt else default.get('system_prompt','')
    system_prompt = Template(system_prompt)
    system_prompt = system_prompt.render(**context)

    input_wrapper = Template(default.get('input', ''))
    input_data = clue_parser(input)
    prompt = input_wrapper.render(**input_data)

    if emoji:
        if emoji.emoji_steps == EmojiSteps.single:
            if emoji.emoji_convention in ('simple', 'full'):
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
            Ollama = ollama.Client(str(model.host) if model.host else os.getenv("OLLAMA_HOST"))
            if 'num_ctx' in model_options.keys():
                if model_options['num_ctx']:
                    return Ollama.generate(
                        model=model.model,
                        system=system_prompt,
                        prompt=prompt,
                        options=model_options
                    )['response']
                else:
                    model_options['num_ctx'] = get_context_size(prompt, system_prompt)
                    return Ollama.generate(
                        model=model.model,
                        system=system_prompt,
                        prompt=prompt,
                        options=model_options
                    )['response']
            else:
                model_options['num_ctx'] = get_context_size(prompt, system_prompt)
                return Ollama.generate(
                    model=model.model,
                    system=system_prompt,
                    prompt=prompt,
                    options=model_options
                )['response']

        case "groq":
            from groq import Groq
            client = Groq(api_key=os.getenv('GROQ_API_KEY'))
            groq_configs = ('top_p','temperature', 'max_tokens')
            groq_options = {config : model_options.get(config) if model_options.get(config) else None for config in (set(tuple(model_options.keys())) & set(groq_configs))}
            return client.chat.completions.create(
                messages=[
                    {
                        "role" : "system",
                        "content" : system_prompt
                    },
                    {
                        "role" : "user",
                        "content" : prompt
                    }
                ],
                model=model.model,
                stream=False,
                **groq_options
            ).choices[0].message.content

        case 'google':
            import google.generativeai as genai
            genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
            model=genai.GenerativeModel(
              model_name=model.model,
              system_instruction=system_prompt)
            return model.generate_content(prompt).text

        case 'openai':
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            openai_configs = ('top_p','temperature', 'max_tokens')
            openai_options = {config : model_options.get(config) if model_options.get(config) else None for config in (set(tuple(model_options.keys())) & set(openai_configs))}
            return client.chat.completions.create(
                messages=[
                    {
                        "role" : "system",
                        "content" : system_prompt
                    },
                    {
                        "role" : "user",
                        "content" : prompt
                    }
                ],
                model=model.model,
                stream=False,
                **openai_options
            ).choices[0].message.content

        case 'custom_openai_compatible':
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv('CUSTOM_API_KEY', default='nokey'), base_url=str(model.host))
            openai_configs = ('top_p','temperature', 'max_tokens')
            openai_options = {config : model_options.get(config) if model_options.get(config) else None for config in (set(tuple(model_options.keys())) & set(openai_configs))}
            return client.chat.completions.create(
                messages=[
                    {
                        "role" : "system",
                        "content" : system_prompt
                    },
                    {
                        "role" : "user",
                        "content" : prompt
                    }
                ],
                model=model.model,
                stream=False,
                **openai_options
            ).choices[0].message.content

        case _:
            raise NotImplementedError("provider not found")
