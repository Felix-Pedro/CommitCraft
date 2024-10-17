from ast import Raise
import subprocess

from requests.api import options
from defaults import default
from enum import Enum
from pydantic import BaseModel, Field, conint, Extra
from typing import Optional, Dict, Union

def get_diff() -> str:
    diff = subprocess.run(['git', 'diff', '--staged', '-M'], capture_output=True, text=True)
    return diff.stdout

def get_context_size(diff, system):
    input_len = len(system) + len(diff)
    num_ctx = int(min(max(input_len*2.64, 1024), 65536))
    return num_ctx

# Define the Emoji Enum
class EmojiEnum(str, Enum):
    simple = 'simple'
    detailed = 'detailed'
    none = 'none'

# Define the model_options structure with restrictions on specific keys
class LModelOptions(BaseModel):
    num_ctx: Optional[int] = None  # Ensure num_ctx is an int in the range or None
    temperature: Optional[float] = Field(ge=0.0, le=1.0, default=0.7)  # Temperature should be a float between 0 and 1
    max_tokens: Optional[conint(ge=1)] = None  # Ensure max_tokens is a positive integer if provided

    class Config:
        extra = Extra.allow

# Define a Pydantic model for validation
class CommitCraftRequest(BaseModel):
    diff: str
    provider: str = 'ollama'
    model: str = 'gemma2'
    context: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt: Optional[str] = None
    lmodel_options: Optional[LModelOptions] = None  # Use the custom ModelOptions type
    emoji: EmojiEnum = EmojiEnum.simple

def commit_craft(request: CommitCraftRequest) -> str:
    context_info = request.context
    system_prompt = None
    if request.context:
        request.context = request.context.strip()
        if request.context.startswith('file:'):
            with open(request.context.lstrip('file:')) as file:
                match request.context.split('.')[-1]:
                    case 'toml':
                        import toml
                        context_info = toml.loads(file.read())
                    case 'yml' | 'yaml':
                        import yaml
                        context_info = yaml.safe_load(file.read())
                    case 'json':
                        import json
                        context_info = json.loads(file.read())
                    case _:
                        context_info = file.read()
        else:
            context_info=request.context
    if request.user_prompt:
        user_prompt = request.user_prompt.strip()
    else:
        user_prompt = None
    if request.system_prompt:
        system_prompt = request.system_prompt.strip()
    elif context_info:
        if isinstance(context_info, dict):
            system_prompt = f'''
            # Proposure
            You are a commit message helper for {context_info["name"]} a project written in {context_info["language"]} described as :
            {context_info["description"]}

            Your only task is to recive a git diff and return a conciveble commit message folowing those gidelines:

            - Never ask for folow-up qucontext_infoestions.
            - Don't ask quetions.
            - Don't talk about yourself.
            - Be concise and clear.
            - Be informative.
            - Don't explain row by row just the global goal of the changes.
            - Avoid unecessary details and long explanations.
            - Use action verbs.
            - Use bullet points in the body if there are many changes
            - Do not talk about the hashes
            {context_info.get("commit_guidelies", default.get("commit_guidelines"))}
            {context_info.get("emoji", default.get("emoji"))}
            '''
    else:
        system_prompt = None
    match request.provider:
        case "ollama":
            import ollama
            if request.lmodel_options:
                model_options = request.lmodel_options.dict()
                if 'num_ctx' in model_options.keys():
                    return ollama.generate(model=request.model, system=system_prompt, prompt=request.diff, options=model_options)
                else:
                    model_options['num_ctx'] = get_context_size(request.diff, system_prompt)
                    return ollama.generate(model=request.model, system=system_prompt, prompt=request.diff, options=model_options)
            else:
                return ollama.generate(model=request.model, system=system_prompt, prompt=request.diff, options={'num_ctx' : get_context_size(request.diff, system_prompt)})
        case _:
            raise NotImplementedError("provider not found")
