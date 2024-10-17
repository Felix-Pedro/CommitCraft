from ast import Raise
import subprocess

from requests.api import options
from defaults import default

def get_diff() -> str:
    diff = subprocess.run(['git', 'diff', '--staged', '-M'], capture_output=True, text=True)
    return diff.stdout

def get_context_size(diff, system):
    input_len = len(system) + len(diff)
    return min(max(input_len*1.5, 1024), 128000)
    

def commit_craft(diff : str,
                provider : str='ollama',
                model : str='llama3.1',
                provider_url : str | None=None,
                context : str | None=None,
                system_prompt : str | None=None,
                user_prompt : str | None=None,
                model_options : dict | None=None) -> str:
    context_info = context
    if context:
        context = context.strip()
        if context.startswith('file:'):
            with open(context.lstrip('file:')) as file:
                match context.split('.')[-1]:
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
            context_info=context
    if user_prompt:
        user_prompt = user_prompt.strip()
    if system_prompt:
        system_prompt = system_prompt.strip()
    elif context:
        if context_info and isinstance(context_info, dict):
            system_prompt = f'''
            # Proposure
            You are a commit message helper for {context_info["name"]} a project written in {context_info["language"]} described as :
            {context_info["description"]}

            Your only task is to recive a git diff and return a conciveble commit message folowing those gidelines:

            - Never ask for folow-up questions.
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
    match provider:
        case "ollama":
            import ollama
            if model_options:
                if 'num_ctx' in model_options.keys():
                    return ollama.generate(model=model, system=system_prompt, prompt=diff, options=model_options)
                else:
                    model_options['num_ctx'] = get_context_size(diff, system_prompt)
                    return ollama.generate(model=model, system=system_prompt, prompt=diff, options=model_options)
            else:
                return ollama.generate(model=model, system=system_prompt, prompt=diff, options={'num_ctx' : get_context_size(diff, system_prompt)})
        case _:
            raise NotImplementedError("provider not found")
