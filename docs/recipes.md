# Recipes & Advanced Usage

Examples and guides for getting the most out of CommitCraft.

## Using CommitClues

**CommitClues** help the AI understand the context and intent behind your changes, resulting in more accurate and relevant commit messages. They work by adding descriptive hints to the prompt sent to the AI model.

### What are CommitClues?

CommitClues are optional flags you can provide to give the AI additional context about your commit. Instead of the AI only seeing code diffs, it also understands *why* you made the changes.

### Available CommitClues

| Clue Type | CLI Flag | Description | Default Message Added to Prompt |
| :--- | :--- | :--- | :--- |
| Bug Fix | `--bug` or `--bug-desc "..."` | Indicates this commit fixes a bug | "This commit focus on fixing a bug" |
| Feature | `--feat` or `--feat-desc "..."` | Indicates this commit adds a new feature | "This commit focus on a new feature" |
| Documentation | `--docs` or `--docs-desc "..."` | Indicates documentation changes | "This commit focus on docs" |
| Refactoring | `--refact` or `--refact-desc "..."` | Indicates code refactoring | "This commit focus on refactoring" |
| Custom | `--context-clue "..."` | Provide any custom context hint | Your custom text |

### Basic Usage (Boolean Flags)

Use the basic flag to add the default description:

```bash
# Bug fix
CommitCraft --bug

# New feature
CommitCraft --feat

# Documentation update
CommitCraft --docs

# Refactoring
CommitCraft --refact
```

**Result:** The AI receives a hint like "This commit focus on fixing a bug" along with the diff.

### Detailed Usage (Description Flags)

Provide specific details about what you changed:

```bash
# Bug fix with details
CommitCraft --bug-desc "Fixed null pointer exception in user login flow"

# Feature with details
CommitCraft --feat-desc "Added dark mode toggle to settings page"

# Documentation with details
CommitCraft --docs-desc "Updated API examples for v2.0 endpoints"

# Refactoring with details
CommitCraft --refact-desc "Extracted authentication logic into separate service"
```

**Result:** The AI receives both the default hint AND your specific description, e.g., "This commit focus on fixing a bug: Fixed null pointer exception in user login flow"

### Custom Context Clues

For situations that don't fit the predefined categories:

```bash
# Version bump
CommitCraft --context-clue "Bump version to 1.0.0 for production release"

# Dependency update
CommitCraft --context-clue "Update React from v17 to v18"

# Performance improvement
CommitCraft --context-clue "Optimize database queries for dashboard page"
```

### Combining Multiple Clues

You can combine multiple clues to provide richer context:

```bash
CommitCraft --feat-desc "Added user profile page" --docs-desc "Added API documentation for profile endpoints"
```

The AI will receive:
```
Clues:
  This commit focus on a new feature: Added user profile page
  This commit focus on docs: Added API documentation for profile endpoints
```

### Using CommitClues with Git Hooks

If you've installed the CommitCraft git hook in **interactive mode** (the default), you'll be prompted for CommitClues automatically:

```bash
git commit

# Hook prompts:
> What type of commit is this?
> [b] Bug fix
> [f] Feature
> [d] Documentation
> [r] Refactoring
> [n] None
> [s] Skip (write message manually)
> Your choice: f

> Describe feature (optional):
> Added dark mode toggle

# CommitCraft runs with: --feat-desc "Added dark mode toggle"
```

**Non-interactive mode:** If you installed with `--no-interactive`, the hook won't prompt and will generate generic messages. Use manual CommitCraft calls with clues instead.

### Best Practices

1. **Be Specific with Descriptions:** `--feat-desc "Added OAuth2 authentication"` is better than just `--feat`
2. **Use for Ambiguous Changes:** When the diff alone doesn't explain *why*, clues help tremendously
3. **Don't Over-Explain:** The AI can see the diff; focus on intent, not implementation details
4. **Combine When Appropriate:** If your commit touches multiple areas, combine relevant clues
5. **Use Interactive Hooks:** The interactive git hook mode makes CommitClues effortless for everyday commits

### How CommitClues Work Internally

CommitClues are appended to the user prompt before sending to the AI:

```
############# Beginning of the diff #############
[your git diff here]
################ End of the diff ################

Clues:
  This commit focus on a new feature: Added dark mode
```

The AI sees both the code changes and the contextual hints, allowing it to generate more accurate commit messages.

---

## Customizing Prompts

You can change the personality or strictness of the commit messages by modifying the system prompt.

### "Conventional Commits" Strict Mode
Enforce strict adherence to the Conventional Commits specification.

**Config (`context.toml`):**
```toml
[models]
system_prompt = """
You are a strict commit message generator.
Rules:
1. Format: <type>(<scope>): <description>
2. Types: feat, fix, docs, style, refactor, test, chore
3. Max 50 chars for the subject line.
4. No emojis.
5. Use imperative mood ("add" not "added").
"""
```

### "Pirate Mode" 🏴‍☠️
Just for fun.

**Config (`context.toml`):**
```toml
[models]
system_prompt = "You are a pirate software engineer. Write commit messages in a pirate accent. Use nautical terms for code concepts."
```

## Advanced Git Hook Workflows

### Two-Step Confirmation for Hooks

When using CommitCraft in a git hook, you might want to review the configuration and token usage before actually making an API call to generate the commit message. The `--confirm` flag enables this workflow.

**Install hook with confirmation mode:**

```bash
# Local repository
CommitCraft hook --confirm

# Global (all new repos)
CommitCraft hook --global --confirm

# Interactive + confirmation
CommitCraft hook --confirm  # Default is interactive
```

**Workflow with confirmation enabled:**

1. Stage your changes: `git add .`
2. Run: `git commit`
3. **Interactive prompt appears** (if interactive mode):
   ```
   CommitCraft: What type of commit is this?
     [b] Bug fix
     [f] Feature
     [d] Documentation
     [r] Refactoring
     [n] None
     [s] Skip
   Your choice: f
   Describe the feature (optional): Added dark mode
   ```
4. **Dry-run preview shows**:
   ```
   ┌─────────────────────────────┬────────────────────────────┐
   │ Metric                      │ Value                      │
   ├─────────────────────────────┼────────────────────────────┤
   │ Token Count                 │ 1390                       │
   │ System Prompt Tokens        │ 156                        │
   │ User Prompt Tokens          │ 1234                       │
   │ Model                       │ qwen3                      │
   │ Provider                    │ ollama                     │
   │ Host                        │ http://localhost:11434     │
   └─────────────────────────────┴────────────────────────────┘
   ```
5. **Confirmation prompt**:
   ```
   Proceed with commit message generation? (Y/n): y
   ```
6. **Message generated** and editor opens with AI-generated commit message

**Why use confirmation in hooks?**

- **Cost Control:** Review token usage before paid API calls (OpenAI, Anthropic, Groq)
- **Context Awareness:** See exactly what will be sent to the LLM
- **Large Diffs:** Verify token count on large changesets before proceeding
- **Configuration Testing:** Ensure correct model/provider before generating

**Enabling/Disabling confirmation per-commit:**

You can control confirmation mode on a per-commit basis using environment variables:

```bash
# Enable confirmation for a single commit (even without --confirm hook)
COMMITCRAFT_CONFIRM=1 git commit

# Disable confirmation for a single commit (even with --confirm hook)
COMMITCRAFT_CONFIRM= git commit  # Empty value disables it

# Skip CommitCraft entirely for this commit
COMMITCRAFT_SKIP=1 git commit

# Provide your own message (auto-skips)
git commit -m "quick fix"
```

### Skipping the Hook
Sometimes you just want to write a quick message without AI assistance.

```bash
# Option 1: Skip hook using environment variable
COMMITCRAFT_SKIP=1 git commit

# Option 2: Auto-skip when providing your own message
git commit -m "quick fix"  # Hook automatically skips

# Option 3: Use interactive menu and choose to skip
git commit
# > What type of commit is this?
# > [s] Skip (write message manually)
# Your choice: s
```

### Cost Control and Token Management

When using paid LLM providers (OpenAI, Anthropic, Groq), it's important to be aware of token usage to control costs. CommitCraft provides several features to help.

**1. Dry-Run Mode (Check Tokens Without Generating):**

The `--dry-run` flag shows token usage statistics **without** making an API call:

```bash
# See token count without making API call
CommitCraft --dry-run

# Example output for Ollama:
# ┌──────────────────────┬──────────────────────────────┐
# │ Metric               │ Value                        │
# ├──────────────────────┼──────────────────────────────┤
# │ Token Count          │ 2579                         │
# │ System Prompt Tokens │ 234                          │
# │ User Prompt Tokens   │ 2345                         │
# │ Model                │ qwen3                        │
# │ Provider             │ ollama                       │
# │ Host                 │ http://localhost:11434       │
# │ Context Size         │ 3869                         │
# │ Context Utilization  │ 66.7%                        │
# └──────────────────────┴──────────────────────────────┘

# Example output for OpenAI/Google/Anthropic/Groq:
# ┌──────────────────────┬──────────────────────┐
# │ Metric               │ Value                │
# ├──────────────────────┼──────────────────────┤
# │ Token Count          │ 2579                 │
# │ System Prompt Tokens │ 234                  │
# │ User Prompt Tokens   │ 2345                 │
# │ Model                │ gpt-4                │
# │ Provider             │ openai               │
# └──────────────────────┴──────────────────────┘
```

**Note:** Dry-run **exits immediately** after showing statistics. Use `--confirm` if you want to generate after reviewing.

**2. Confirmation Mode (Review Before Generating):**

```bash
# Shows dry-run stats, then asks for confirmation
CommitCraft --confirm --provider openai --model gpt-4

# Step 1: Shows token preview
# Step 2: Prompts "Proceed with commit message generation? (Y/n)"
```

**3. Ignore Large Files to Reduce Tokens:**

Create `.commitcraft/.ignore` to exclude files that add noise:

```bash
# Generate default ignore file
CommitCraft config --generate-ignore

# Add custom patterns
echo "*.svg" >> .commitcraft/.ignore
echo "dist/*" >> .commitcraft/.ignore
echo "build/*" >> .commitcraft/.ignore
```

**4. Use Local Models for Development:**

Use free local models (Ollama) during development, paid models for important commits:

```bash
# Development: Free local model
CommitCraft --provider ollama --model qwen3

# Production release: Paid high-quality model
CommitCraft --confirm --provider openai --model gpt-4 --feat-desc "v2.0 release"
```

**5. Set Token Limits:**

```bash
# Limit output tokens (commit message length)
CommitCraft --max-tokens 150

# Or in config file
[models.options]
max_tokens = 150
```

**6. Monitor Usage with Aliases:**

Create shell aliases for different use cases:

```bash
# ~/.bashrc or ~/.zshrc
alias cc-check="CommitCraft --dry-run"
alias cc-cheap="CommitCraft --provider ollama --model qwen3"
alias cc-premium="CommitCraft --confirm --provider openai --model gpt-4"
```

**Example Workflow:**

```bash
# 1. Check token usage first
CommitCraft --dry-run --provider openai --model gpt-4
# Output shows 5000 tokens (might be expensive)

# 2. Reduce tokens by ignoring files
echo "package-lock.json" >> .commitcraft/.ignore

# 3. Check again
CommitCraft --dry-run --provider openai --model gpt-4
# Output shows 1500 tokens (much better!)

# 4. Generate with confirmation
CommitCraft --confirm --provider openai --model gpt-4
```

### Chaining with `pre-commit`
If you use the [pre-commit](https://pre-commit.com/) framework for linting, CommitCraft runs as a `prepare-commit-msg` hook, which executes *after* `pre-commit` hooks pass but *before* the editor opens. This is the ideal workflow:
1. `pre-commit` fixes linting issues.
2. `CommitCraft` sees the final staged changes and generates the message.

## CI/CD Integration

### GitHub Actions: Auto-Suggest PR Description
You can use CommitCraft to generate a description for a Pull Request.

*Note: This requires `commitcraft` to be installed in the runner.*

```yaml
steps:
  - uses: actions/checkout@v3
  - name: Install CommitCraft
    run: pipx install commitcraft
  - name: Generate PR Description
    env:
      GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
    run: |
      git diff origin/main > diff.txt
      # Pipe diff to commitcraft (future feature or use script wrapper)
      # Currently CommitCraft reads from git diff --staged.
      # Workaround: Stage files in CI environment?
```
*(Note: CI integration is easier if you use the library API directly in a Python script)*

## Using as a Library

CommitCraft can be imported in Python scripts to build custom automation tools.

```python
from commitcraft import commit_craft, CommitCraftInput, LModel

# Define input
my_input = CommitCraftInput(diff="diff --git a/main.py b/main.py...")

# Configure model
model = LModel(provider="ollama", model="qwen3")

# Generate
message = commit_craft(input=my_input, models=model)
print(message)
```
