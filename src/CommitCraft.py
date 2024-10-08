from git import Repo

def get_diff():
    repo = Repo(".")  # Assuming you are running this script in the root of your repository
    index = repo.index
    diff = index.diff("HEAD", create_patch=True)
    return [str(diff) for diff in diff]

def commit_craft(diff, ):
    pass