from ast import Raise
import subprocess
from typing_extensions import List
from .defaults import default
from enum import Enum
from pydantic import BaseModel, Field, conint, Extra
from typing import Optional, Dict, Union

def get_diff() -> str:
    diff = subprocess.run(['git', 'diff', '--staged', '-M'], capture_output=True, text=True)
    return diff.stdout

def get_context_size(diff, system):
    input_len = len(system) + len(diff)
    num_ctx = int(min(max(input_len*2.64, 1024), 128000))
    return num_ctx

# Define the Emoji Enum
class EmojiSteps(Enum):
    single = 'single'
    step2 = '2-step'
    false = False

# Define the model_options structure with restrictions on specific keys
class LModelOptions(BaseModel):
    num_ctx: Optional[int] = None
    temperature: Optional[float] = None
    max_tokens: Optional[conint(ge=1)] = None  # Ensure max_tokens is a positive integer if provided

    class Config:
        extra = Extra.allow

class Provider(str, Enum):
    ollama = 'ollama'
    openai = 'openai'
    google = 'google'
    groq = 'groq'

class LModel(BaseModel):
    provider: Provider = Provider.ollama
    model: str = 'gemma2'
    system_prompt: Optional[str] = None
    options: Optional[LModelOptions] = None

class Context(BaseModel):
    project_name: Optional[str] = None
    project_language: Optional[str] = None
    project_description: Optional[str] = None
    commit_guidelines: Optional[str] = None

class EmojiConfig(BaseModel):
    emoji_steps: EmojiSteps = EmojiSteps.single
    emoji_convention: str = "simple"
    emoji_model: Optional[LModel] = None

class CommitCraftRequest(BaseModel):
    diff: str
    models: LModel = LModel() # Will support multiple models in 1.1.0 but for now only one
    emoji: EmojiConfig = EmojiConfig()
    context: Optional[Context] = None

def commit_craft(request: CommitCraftRequest) -> str:
    context_info = request.context
    system_prompt = request.models.system_prompt
    if not system_prompt and context_info:
        if (context_info.project_name and context_info.project_language and context_info.project_description):
            system_prompt = f'''
# Proposure

You are a commit message helper for {context_info.project_name} a project written in {context_info.project_language} described as :

{context_info.project_description}

Your only task is to recive a git diff and return a simple commit message folowing these guidelines:

{context_info.commit_guidelines if context_info.commit_guidelines else  default.get("commit_guidelines")}
            '''.strip()
        else:
            system_prompt = f'''
# Proposure

You are a commit message helper.

Your only task is to recive a git diff and return a simple commit message folowing these guidelines:

{context_info.commit_guidelines if context_info.commit_guidelines else  default.get("commit_guidelines")}
            '''.strip()
    elif not system_prompt and not context_info:
        system_prompt = f'''
# Proposure

You are a commit message helper.

Your only task is to recive a git diff and return a simple commit message folowing these guidelines:

{default.get("commit_guidelines")}
        '''.strip()
    emoji = request.emoji
    if emoji.emoji_steps == EmojiSteps.single:
        if emoji.emoji_convention in ('simple', 'full'):
            system_prompt+=f'\n\n{default.get('emoji_guidelines', {}).get(emoji.emoji_convention)}'
        elif emoji.emoji_convention:
            system_prompt+=f'\n\n{emoji.emoji_convention}'
    model = request.models
    match model.provider:
        case "ollama":
            import ollama
            if model.options:
                model_options = model.options.dict()
                if 'num_ctx' in model_options.keys():
                    if model_options['num_ctx']:
                        return ollama.generate(model=model.model, system=system_prompt, prompt=request.diff, options=model_options)
                    else:
                        model_options['num_ctx'] = get_context_size(request.diff, system_prompt)
                        return ollama.generate(model=model.model, system=system_prompt, prompt=request.diff, options=model_options)
                else:
                    model_options['num_ctx'] = get_context_size(request.diff, system_prompt)
                    return ollama.generate(model=model.model, system=system_prompt, prompt=request.diff, options=model_options)
            else:
                return ollama.generate(model=model.model, system=system_prompt, prompt=request.diff, options={'num_ctx' : get_context_size(request.diff, system_prompt)})
        case _:
            raise NotImplementedError("provider not found")
