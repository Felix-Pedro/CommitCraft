# Future Improvements & Roadmap

This document outlines planned features, improvements, and community suggestions for future versions of CommitCraft.

---

## Already Possible! ✅

Before diving into future features, here are some capabilities that **already work** in CommitCraft but might not be obvious:

### Multi-Language Commit Messages
You can generate commits in any language by configuring your `commit_guidelines` in that language:
```toml
[context]
commit_guidelines = "Genera mensajes en español..."
```

### Team Configuration Sharing
Share settings across your team by committing the `.commitcraft/` folder to your repository:
```bash
git add .commitcraft/
git commit -m "feat: add team CommitCraft config"
```

### Interactive Editing (via Git Hook)
The git hook has interactive mode that lets you provide CommitClues before generation:
```bash
CommitCraft hook  # Install with interactive prompts
git commit  # Prompts for bug/feature/docs/refactor before generating
```

### Custom Commit Styles
Already fully customizable via `system_prompt` and `commit_guidelines`:
```toml
[models]
system_prompt = "Your custom instructions..."

[context]
commit_guidelines = "Your format rules..."
```

See the full documentation for more details on these features!

---

## Planned for v1.2 🎯

### Two-Step Emoji System
**Status**: Documented, not yet implemented
**Complexity**: Medium
**Time Estimate**: 2-3 weeks

Currently, CommitCraft generates the commit message and emoji in a single LLM call. The two-step system would:

1. **Step 1**: Generate the commit message without emoji
2. **Step 2**: Make a second, focused LLM call to select the most appropriate emoji based on the message

**Benefits**:
- More accurate emoji selection
- Better separation of concerns
- Allows using faster/cheaper models for emoji selection
- Enables emoji-specific prompting strategies

**Configuration**:
```toml
[emoji]
emoji_steps = "2-step"  # Will be available in v1.2
emoji_model = "gpt-4o-mini"  # Optional: use different model for emoji selection
```

**Implementation Notes**:
- Add `emoji_model` config option for separate model
- Create focused emoji selection prompt
- Handle emoji injection into existing message
- Update tests for two-step flow

### Rich TUI Config Interface
**Status**: Planned for v1.2
**Complexity**: Medium
**Time Estimate**: 3-4 weeks

Transform the `config` subcommand from simple text prompts to a modern, beautiful terminal UI with arrow key navigation, visual menus, and interactive wizards - similar to Claude CLI, Gemini CLI, and other modern CLI tools.

**Planned Features**:
- Arrow key navigation for provider/model selection
- Visual selection menus with descriptions
- Input validation with inline error messages
- Spinner animations for API calls
- Step-by-step wizard flow with progress indicators
- Configuration preview with syntax highlighting

**Implementation Approach**:
- Start with **InquirerPy** for quick implementation
- Combine with existing Rich library for output and spinners
- Option to migrate to **Textual** later for more advanced TUI features

**Benefits**:
- Faster, more intuitive setup process
- Reduced configuration errors
- Professional, modern user experience
- Better discoverability of features

> **Note for Contributors**: Detailed implementation specification available in `cache/.aimd/tui-config-implementation-spec.md`

### AUR (Arch User Repository) Package
**Status**: Planning complete, awaiting implementation
**Complexity**: Low (packaging) + Low (maintenance)
**Time Estimate**: 3-4 hours initial setup, 5-10 min per release

Create official Arch Linux package for easier installation on Arch-based distributions.

**Package Names**:
- `commitcraft` - Stable releases from PyPI
- `commitcraft-git` - Development version from GitHub

**Benefits**:
- Native installation: `yay -S commitcraft`
- Automatic dependency resolution via pacman
- Better integration with Arch Linux ecosystem

**Implementation Status**:
- ⏳ PKGBUILD template created (`docs/aur/PKGBUILD`)
- ⏳ Publishing guide documented (`docs/aur/README.md`)
- ⏳ Awaiting v1.1.0 release for initial publish
- ⏳ AUR account setup

**Maintenance**: Update PKGBUILD version and checksums after each PyPI release

---

## Future Ideas 💡 (no definitive version)


### 1. Commit Message Templates
**Priority**: Medium
**Complexity**: Medium
**Use Case**: Organizations with strict commit conventions

Allow users to define custom templates that the LLM must follow. Needs to enforce validation of template usage.

**Example Configuration**:
```toml
[templates]
default = """
Type: {type}
Scope: {scope}
Summary: {summary}

Details:
{details}

Issue: {issue}
"""

bug = """
🐛 Bug Fix: {summary}

Root Cause: {cause}
Solution: {solution}
Tested: {testing}

Fixes #{issue}
"""
```

**Usage**:
```bash
CommitCraft --template bug
# AI fills in template fields based on diff
```

**Benefits**:
- Consistent commit format across team
- Enforces required fields
- Reduces prompt engineering needed

---

### 2. Conventional Commits Strict Mode
**Priority**: Medium
**Complexity**: Low
**Use Case**: Teams using conventional commits

Enforce strict conventional commit format: `type(scope): subject`

**Configuration**:
```toml
[conventional_commits]
enabled = true
types = ["feat", "fix", "docs", "style", "refactor", "test", "chore"]
require_scope = true
require_body = false
max_subject_length = 50
```

**Validation**:
- Post-generation validation
- Reject if format doesn't match
- Provide feedback and regenerate

**Example Output**:
```
feat(auth): add OAuth2 login support

Implemented OAuth2 authentication flow using...
```

---

### 3. Multi-Language Commit Messages
**Priority**: Low (Already Achievable)
**Complexity**: Low
**Status**: ✅ Already possible via configuration

**Note**: You can already generate commit messages in any language by configuring the commit guidelines in that language!

**How to Use Today**:
```toml
[context]
commit_guidelines = """
Genera mensajes de commit en español siguiendo estas reglas:
- Usa verbos en infinitivo
- Sé conciso y claro
- Explica el qué y el por qué
"""
```

Or add to your system prompt:
```toml
[models]
system_prompt = """
You are a commit message helper.
**IMPORTANT: Generate all commit messages in Spanish.**
...
"""
```

**Potential Enhancement** (future):
- Add `--language` CLI flag as shortcut
- Pre-configured language templates
- Automatic GitMoji translations

---

### 4. Issue Tracker Integration
**Priority**: Medium
**Complexity**: High
**Use Case**: Link commits to issues automatically

Automatically detect and link commits to issue tracker tickets.

**Supported Trackers** (proposed):
- GitHub Issues
- GitLab Issues
- Jira
- Linear
- Asana

**Features**:
- Auto-detect branch naming (e.g., `fix/PROJ-123-auth-bug`)
- Extract issue numbers from commits
- Fetch issue details from API
- Include issue context in commit message

**Configuration**:
```toml
[issue_tracker]
type = "jira"
base_url = "https://company.atlassian.net"
project_key = "PROJ"
api_token = "${JIRA_API_TOKEN}"
auto_link = true
include_issue_title = true
```

**Example Output**:
```
fix: resolve authentication timeout issue

Fixed session timeout not being properly checked in auth middleware.

Related to PROJ-123: Users logged out unexpectedly
```

---

### 5. Team Conventions & Shared Config
**Priority**: Low (Already Works)
**Complexity**: Low
**Status**: ✅ Already possible by committing `.commitcraft/` folder

**Note**: Team configuration sharing already works! Just commit your `.commitcraft/` folder to the repository.

**How to Use Today**:
```bash
# Team leader sets up config
mkdir .commitcraft
# ... configure settings ...
git add .commitcraft/
git commit -m "feat: add team CommitCraft configuration"
git push

# Team members automatically get the config
git pull
CommitCraft  # Uses team config automatically!
```

**How It Works**:
- Project-level config (`.commitcraft/`) overrides global config
- Everyone on the team gets the same settings
- API keys still come from individual `.env` files (not committed)
- Local users can still override with CLI flags

**Potential Enhancement** (future):
- Remote config fetching from URL (for non-git workflows)
- Config inheritance and merging strategies
- Validation tools for team configs
- Centralized config repository templates

---

### 6. Commit Message Quality Scoring
**Priority**: Low
**Complexity**: Medium
**Use Case**: Improve message quality awareness

Rate the generated commit message on various quality metrics. (on comments after the message so the user can perfect it)

**Metrics**:
- **Clarity**: Is the message clear and understandable?
- **Completeness**: Does it explain what and why?
- **Conciseness**: Is it appropriately brief?
- **Convention**: Does it follow project conventions?
- **Context**: Does it provide enough background?

**Output**:
```
Generated Commit Message:
fix: resolve authentication timeout

Quality Score: 7.5/10
  ✅ Clarity: 9/10 - Clear and specific
  ⚠️  Completeness: 6/10 - Missing "why" explanation
  ✅ Conciseness: 9/10 - Appropriate length
  ✅ Convention: 8/10 - Follows format
  ⚠️  Context: 6/10 - Could provide more background

Suggestions:
- Add explanation of root cause
- Mention testing performed
```

**Configuration**:
```toml
[quality_scoring]
enabled = true
show_suggestions = true
require_minimum_score = 7.0
```

---

### 7. Pre-Commit Message Validation
**Priority**: Medium
**Complexity**: Low
**Use Case**: Enforce commit message rules

Validate generated messages against configurable rules before accepting.

**Validation Rules**:
```toml
[validation]
enabled = true

[validation.rules]
max_subject_length = 50
min_subject_length = 10
require_body = false
min_body_length = 20
forbidden_words = ["WIP", "TODO", "FIXME", "test", "asdf"]
required_patterns = ["^(feat|fix|docs|style|refactor|test|chore)"]
```

**Behavior**:
- Validate after generation
- Show validation errors
- Offer to regenerate if validation fails
- Allow override with `--skip-validation`

**Example**:
```
❌ Validation Failed:
  - Subject exceeds 50 characters (current: 67)
  - Subject contains forbidden word: "WIP"

Regenerate? [Y/n]
```

---

### 8. Batch Commit Mode
**Priority**: Low
**Complexity**: High
**Use Case**: Multiple logical changes in staging

Generate separate commit messages for different file groups in staging area.

**Workflow**:
1. User stages multiple unrelated changes
2. CommitCraft detects distinct change groups
3. Generates separate messages for each group
4. Offers to create multiple commits

**Example**:
```bash
CommitCraft --batch

Detected 3 distinct change groups:
  1. Frontend changes (app.tsx, styles.css) - 15 files
  2. Backend API updates (api.py, models.py) - 8 files
  3. Documentation (README.md, docs/) - 3 files

Generate separate commits? [Y/n]

Generated:
  Commit 1: feat: add dark mode toggle to UI
  Commit 2: refactor: simplify API error handling
  Commit 3: docs: update installation instructions

Create these commits? [Y/n]
```

**Challenges**:
- Detecting logical groupings (ranges from simple heuristics to AI-hard semantic understanding)
- Handling overlapping changes (files that belong to multiple logical groups)
- Complex git staging operations (unstaging/restaging subsets)

**Implementation Approaches** (configurable options):

1. **Heuristic-based grouping** 🟢 *Reduces costs*
   - Group by directory: `frontend/`, `backend/`, `docs/`
   - Group by file type: `.tsx` files, `.py` files, `.md` files
   - Group by naming patterns: test files, config files, source files
   - **Pro**: Fast, no API cost, deterministic
   - **Con**: Limited - won't understand semantic relationships
   - **Token impact**: ✅ No extra LLM calls

2. **Local/lightweight model classification** 🟡 *May reduce costs*
   - Use local ML model (scikit-learn, small transformer) for grouping
   - Or use very cheap/fast LLM (gemini-flash-8b, gpt-4o-mini)
   - **Pro**: Better than heuristics, potentially cheaper than main model
   - **Con**: Setup complexity, still costs tokens if using LLM
   - **Token impact**: ⚠️ Minimal cost if local, small cost if using cheap LLM
   - **Example**: Use gpt-4o-mini ($0.15/1M input tokens) for grouping, then gpt-4o ($2.50/1M) for messages

3. **User-guided grouping** 🟢 *Reduces costs*
   - Prompt user to categorize file groups interactively
   - Show file list, let user assign to groups manually
   - **Pro**: Accurate, user has full control, no API cost
   - **Con**: Not automatic, requires user time
   - **Token impact**: ✅ No extra LLM calls

4. **LLM-based intelligent grouping** 🔴 *Increases costs*
   - Use same LLM to analyze diffs and suggest groups semantically
   - Most accurate - understands code relationships
   - **Pro**: Truly intelligent, automatic, best quality
   - **Con**: Doubles LLM API costs, slower
   - **Token impact**: ❌ Full LLM call for grouping + separate calls for each commit message
   - **Use case**: When quality matters more than cost

**Configuration**:
```toml
[batch]
grouping_strategy = "heuristic"  # Options: heuristic, local_model, llm, user_guided
local_model_path = "~/.commitcraft/models/classifier.pkl"  # For local_model
grouping_llm = "gpt-4o-mini"  # For llm strategy - use cheaper model
```

**Recommendation**: Start with heuristics (free), offer LLM as opt-in quality upgrade

---

### 9. Web UI for Configuration
**Priority**: Very Low
**Complexity**: High
**Use Case**: User-friendly setup

Browser-based configuration interface for easier setup.

**Features**:
- Visual configuration editor
- Provider connection testing
- Live commit message preview
- Template builder
- Team config sharing

**Tech Stack** (proposed):
- FastAPI backend
- React/Vue frontend
- Runs locally: `CommitCraft ui`

**Mockup**:
```
┌─────────────────────────────────────────┐
│  CommitCraft Configuration UI           │
├─────────────────────────────────────────┤
│  Providers                              │
│    [✓] Ollama     [Host: localhost]     │
│    [✓] OpenAI     [API Key: ******]     │
│    [ ] Groq       [Setup]               │
│                                         │
│  Context                                │
│    Project Name: MyProject              │
│    Language: Python                     │
│                                         │
│  [Test Connection] [Save Config]        │
└─────────────────────────────────────────┘
```

---

### 10. Plugin System
**Priority**: Low
**Complexity**: Very High
**Use Case**: Community-contributed providers and features

Allow third-party plugins for custom providers, validators, and enhancers.

**Plugin Types**:
- **Provider Plugins**: Custom LLM integrations
- **Validator Plugins**: Custom validation rules
- **Template Plugins**: Specialized message formats
- **Analyzer Plugins**: Custom diff analysis

**Plugin API** (conceptual):
```python
from commitcraft.plugins import ProviderPlugin

class CustomLLMProvider(ProviderPlugin):
    def __init__(self, config):
        self.api_key = config.get("api_key")

    def generate_message(self, diff, context):
        # Custom LLM call
        return "Generated commit message"

    def calculate_usage(self, prompt):
        # Token counting
        return {"input_tokens": 100, "output_tokens": 50}
```

**Configuration**:
```toml
[plugins]
enabled = true
plugins_dir = "~/.commitcraft/plugins"
installed = ["custom-llm", "jira-validator", "emoji-plus"]
```

**Challenges**:
- Plugin security (sandboxing)
- API stability
- Documentation and examples
- Plugin discovery and distribution

---

### 11. Diff Preprocessing & Filtering

**Priority**: Medium
**Complexity**: Medium
**Use Case**: Better focus on relevant changes

Advanced diff filtering and preprocessing before sending to LLM.

**Features**:
- **Semantic Diff**: Focus on meaningful changes, ignore whitespace/formatting (using git diff options)
- **Noise Reduction**: Filter out generated code, lock files, minified files (already partially available via `.commitcraft/.ignore`)
- **File Grouping (Heuristic-Based)**: Group related files using simple rules:
  - **Directory-based**: Files in same folder
  - **Extension-based**: Same file type (.py, .js, etc.)
  - **Naming patterns**: `component.tsx` + `component.test.tsx` + `component.css`
  - **Git history**: Files frequently changed together (analyze git log)

**Configuration**:
```toml
[diff_processing]
semantic_diff = true  # Use git diff -w, --ignore-all-space, etc.
ignore_whitespace = true
ignore_comments = false
group_by_directory = true
group_by_extension = true
detect_test_files = true  # Group tests with implementation

[diff_processing.filters]
ignore_patterns = ["*.lock", "*.min.js", "*.min.css", "*_generated.*"]
focus_on_extensions = [".py", ".js", ".ts", ".go"]
```

**Benefits**:
- Reduced token usage (less noise sent to LLM)
- More focused commit messages
- Better handling of large diffs

**Implementation Approaches** (token reduction focus):

1. **Heuristic filtering** 🟢 *Primary goal: Reduce tokens*
   - Use git diff options (`-w`, `--ignore-all-space`)
   - Filter by file patterns (`.commitcraft/.ignore` already does this!)
   - Simple pattern matching (test files, docs files, config files)
   - **Token impact**: ✅ Reduces tokens sent to LLM
   - **Pro**: Fast, free, effective for common cases
   - **Con**: Can't understand semantic importance

2. **Diff summarization** 🟢 *Reduces tokens significantly*
   - For large files: "50 lines changed in config.json" instead of full diff
   - Provide file tree structure for context: `frontend/components/Button.tsx (+45, -12)`
   - Show function signatures instead of full implementations
   - **Token impact**: ✅ Major token reduction for large changes
   - **Pro**: Handles massive diffs, still gives LLM context
   - **Con**: LLM has less detail for message generation

3. **Local lightweight classifier** 🟡 *Categorize changes*
   - Use local ML model (scikit-learn, small transformer)
   - Or rule-based categorization (test file = "test", docs = "documentation")
   - Categorize: refactor vs bugfix vs feature vs docs
   - **Token impact**: ✅ No extra LLM calls if local
   - **Pro**: Provides structured context to LLM
   - **Con**: Setup complexity, may not be accurate

4. **LLM-based smart filtering** 🔴 *Quality over cost*
   - Use LLM to identify most important changes before generating message
   - Ask LLM: "Which of these files are most relevant for the commit message?"
   - Send filtered subset to main message generation
   - **Token impact**: ❌ Adds LLM call but may reduce tokens in final call
   - **Pro**: Intelligent, context-aware filtering
   - **Con**: Extra cost, may not reduce overall tokens
   - **Use case**: Very large diffs where manual filtering is impractical

**Configuration**:
```toml
[diff_processing]
# Token reduction strategies
semantic_diff = true
ignore_whitespace = true
summarize_large_files = true  # Files >200 lines show summary
max_diff_lines = 500  # Hard limit per file

# Categorization strategy
categorization = "heuristic"  # Options: heuristic, local_model, llm, none

# Smart filtering (optional, costs tokens)
smart_filtering = false  # Set true to use LLM for pre-filtering
smart_filtering_model = "gpt-4o-mini"  # Cheap model for filtering
```

**Best Practices**:
- Start with aggressive heuristic filtering (free, effective)
- Use summarization for large diffs
- LLM-based filtering is optional quality upgrade, not default

---

### 12. Commit Message Refinement Loop

**Priority**: Low
**Complexity**: Medium
**Use Case**: Iteratively improve message quality

Allow users to request improvements to the generated message.

**Workflow**:
```bash
CommitCraft

Generated: "fix: update authentication"

Refine message? [Y/n] Y
  1. Make it more detailed
  2. Make it more concise
  3. Add technical context
  4. Change tone (formal/casual)
  5. Regenerate from scratch

Choice: 1

Refined: "fix: resolve session timeout in JWT authentication middleware

Fixed an issue where JWT tokens were not being properly validated for
expiration, causing users to be unexpectedly logged out."

Accept this message? [Y/n]
```

**Features**:
- Interactive refinement
- Multiple refinement passes
- Keep history of refinements
- Learn from user preferences

---


## Community Contributions Welcome! 🤝

We welcome community contributions for any of these features! Before starting work on a major feature:

1. **Open an issue** to discuss the feature
2. **Check the roadmap** to see if it's already planned
3. **Review the contribution guide** in `CONTRIBUTING.md`
4. **Coordinate with maintainers** to avoid duplicate work

**Good First Issues**:
- Conventional commits validation (Feature #2)
- Multi-language support (Feature #3)

**Advanced Contributors**:
- Two-step emoji system (v1.2)
- Issue tracker integration (Feature #4)
- Plugin system (Feature #10)
- Batch commit mode (Feature #8)

---

## Feature Request Process 📬

Have an idea not listed here? We'd love to hear it!

1. **Search existing issues** to avoid duplicates
2. **Open a feature request** on GitHub Issues
3. **Describe the use case** - why is this useful?
4. **Provide examples** - what would usage look like?
5. **Consider trade-offs** - complexity, maintenance, etc.

**Feature Request Template**:
```markdown
## Feature Request: [Title]

**Problem/Use Case**:
Describe the problem this feature solves or the use case it enables.

**Proposed Solution**:
How would this feature work? Include examples.

**Alternatives Considered**:
Are there other ways to achieve this?

**Additional Context**:
Screenshots, mockups, related issues, etc.
```

---

## Versioning & Release Strategy 📦

**Version Scheme**: Semantic Versioning (SemVer)

- **Major (x.0.0)**: Breaking changes, major architectural shifts
- **Minor (1.x.0)**: New features, non-breaking changes
- **Patch (1.1.x)**: Bug fixes, small improvements

**Release Cadence**:
- **Major releases**: as needed
- **Minor releases**: Every 5-6 months
- **Patch releases**: As needed for critical bugs

**Current Plan**:
- v1.1.0: Current release (January 2026)
- v1.2.0: Two-step emoji, AUR package (Q2 2026)
- v1.3.0: Interactive editing, templates (Q4 2026)
- v2.0.0: Plugin system, major refactor (2027)

---

## Feedback & Discussion 💬

Join the conversation about CommitCraft's future:

- **GitHub Issues**: https://github.com/Felix-Pedro/CommitCraft/issues
- **Discussions**: https://github.com/Felix-Pedro/CommitCraft/discussions

Your feedback shapes CommitCraft's roadmap! 🚀
