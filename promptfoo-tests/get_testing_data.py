import requests
import os
import csv
import random
from dotenv import load_dotenv
load_dotenv()

GITHUB_API_URL = "https://api.github.com"
ACCESS_TOKEN = os.getenv("GITHUB_TOKEN")  # Set your GitHub token as an environment variable

POPULAR_LANGUAGES = ["JavaScript", "Python", "Java",
    "C#", "HTML", "C++", "TypeScript", "CSS", "Shell",
    "SQL", "Scala", "Rust", "Kotlin", "Swift", "Lua"]

def search_repositories(language, license="mit", limit=5):
    """Search repositories based on language and license, ordered by stars."""
    headers = {'Authorization': f'token {ACCESS_TOKEN}'}
    search_url = f"{GITHUB_API_URL}/search/repositories?q=language:{language}+license:{license}&sort=stars&order=desc"
    response = requests.get(search_url, headers=headers)
    repos = response.json()
    repos = repos['items'][:limit]  # Get top repositories (limit)
    return [(repo['owner']['login'], repo['name']) for repo in repos]

def get_repo_details(owner, repo):
    """Fetch repository details including name, description, language, and random 3 commits from the last 10."""
    headers = {'Authorization': f'token {ACCESS_TOKEN}'}

    # Get repo details
    repo_url = f"{GITHUB_API_URL}/repos/{owner}/{repo}"
    repo_data = requests.get(repo_url, headers=headers).json()

    # Get the last 10 commits
    commits_url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/commits"
    commits_data = requests.get(commits_url, headers=headers).json()[:100]

    # Randomly select 3 commits from the last 100
    selected_commits = random.sample(commits_data, 3)

    commits = []
    for i, commit in enumerate(selected_commits, 1):  # Numbering commits (starting from 1)
        commit_message = commit['commit']['message']
        sha = commit['sha']

        # Get the diff for this commit
        diff_url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/commits/{sha}"
        diff_data = requests.get(diff_url, headers=headers).json()
        diff = diff_data.get('files', [{}])[0].get('patch', '')

        commits.append({
            'number': i,
            'message': commit_message,
            'sha': sha,
            'diff': diff
        })

    return {
        "name": repo_data.get('name'),
        "language": repo_data.get('language'),
        "description": repo_data.get('description'),
        "commits": commits
    }

def save_to_csv(data, filename="./promptfoo-tests/test_repos_data.csv"):
    """Save all project details and commits to a CSV file."""
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["name", "language", "description", "commit number", "commit message", "Commit SHA", "diff"])

        for language_data in data.values():
            for repo in language_data:
                for commit in repo['commits']:
                    writer.writerow([
                        repo["name"],
                        repo["language"],
                        repo["description"],
                        commit["number"],
                        commit["message"],
                        commit["sha"],
                        commit["diff"]
                    ])

def process_popular_languages(languages):
    """Process the most popular languages and aggregate data from their top repositories."""
    all_data = {}
    for language in languages:
        print(f"Processing language: {language}")
        repos = search_repositories(language)
        language_data = []
        for owner, repo in repos:
            try:
                print(f"Fetching data for repo: {owner}/{repo}")
                project_data = get_repo_details(owner, repo)
                language_data.append(project_data)
            except Exception as e:
                print(f"Failed to process {owner}/{repo}: {e}")
        all_data[language] = language_data

    save_to_csv(all_data)

if __name__ == "__main__":
    # Process the 15 most popular languages and get 5 repositories and 3 commits for each
    process_popular_languages(POPULAR_LANGUAGES)
