import os
from dotenv import load_dotenv
from CommitCraft import commit_craft, get_diff
import argparse

load_dotenv()

def main():
    diff = get_diff()
    if os.path.exists('./.commitcraft/context.toml'):
        context = 'file:./.commitcraft/context.toml'
    elif os.path.exists('./.commitcraft/context.yaml'):
        context = 'file:./.commitcraft/context.yaml'
    elif os.path.exists('./.commitcraft/context.yml'):
        context = 'file:./.commitcraft/context.yml'
    elif os.path.exists('./.commitcraft/context.json'):
        context = 'file:./.commitcraft/context.json'
    else:
        context = None

    return commit_craft(diff, context=context)
if __name__ == '__main__':
    print(main())
    