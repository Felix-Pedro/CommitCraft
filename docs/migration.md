# Migration Guide

This guide helps you upgrade CommitCraft and adapt to breaking changes between versions.

## Upgrading CommitCraft

```bash
# Using pipx (recommended)
pipx upgrade commitcraft

# Or with specific extras
pipx upgrade commitcraft[all-providers]
```

After upgrading, update your git hooks if you're using them:
```bash
# Local hook
CommitCraft hook

# Global hook
CommitCraft hook --global
```

---

## Migrating from v0.x to v1.0.0

CommitCraft v1.0.0 introduces several breaking changes and new features. This section helps you migrate smoothly.

### Breaking Changes

#### 1. Provider Rename: `custom_openai_compatible` → `openai_compatible`

**Old (v0.x):**
```toml
[models]
provider = "custom_openai_compatible"
model = "deepseek-chat"
host = "https://api.deepseek.com"
```

**New (v1.0.0+):**
```toml
[models]
provider = "openai_compatible"  # Renamed for clarity
model = "deepseek-chat"
host = "https://api.deepseek.com"
```

**CLI Migration:**
```bash
# Old
CommitCraft --provider custom_openai_compatible --model deepseek-chat --host https://api.deepseek.com

# New
CommitCraft --provider openai_compatible --model deepseek-chat --host https://api.deepseek.com
```

**Action Required:**
- Update all config files to use `openai_compatible`
- Update any scripts or aliases
- Update git hooks if they specify the provider

#### 2. Model Options Are No Longer Named Arguments

In v0.x, extra model options were passed as named CLI arguments. In v1.0.0, they're configured in the `[models.options]` section.

**Old (v0.x):**
```bash
# CLI with named arguments (no longer supported)
CommitCraft --provider ollama --model qwen3 --num_ctx 8192 --top_p 0.9
```

**New (v1.0.0+):**
```toml
# Configuration file
[models]
provider = "ollama"
model = "qwen3"

[models.options]
num_ctx = 8192
top_p = 0.9
temperature = 0.7
max_tokens = 500
```

**CLI Still Works For Core Options:**
```bash
# These core options still work as CLI flags
CommitCraft --temperature 0.7 --max-tokens 500 --num-ctx 8192
```

**Action Required:**
- Move non-standard options to config files under `[models.options]`
- Standard options (`temperature`, `max_tokens`, `num_ctx`) still work as CLI flags

#### 3. Named Provider Environment Variables

Environment variable naming for named providers has changed for consistency.

**Old (v0.x):**
```bash
# Pattern was unclear/inconsistent
PROVIDER_NICKNAME_API_KEY=xxx
```

**New (v1.0.0+):**
```bash
# Clear pattern: NICKNAME_API_KEY (uppercase)
LITELLM_API_KEY=xxx
REMOTE_OLLAMA_API_KEY=xxx
DEEPSEEK_API_KEY=xxx
```

**Action Required:**
- Rename environment variables in your `.env` files
- Update CI/CD secrets to match new naming pattern
- Pattern: `{NICKNAME}_API_KEY` where nickname is uppercase

---

### New Features in v1.0.0

Take advantage of these new capabilities:

#### 1. Ollama Cloud Support

Native support for Ollama's cloud service:

```toml
[models]
provider = "ollama_cloud"
model = "qwen3"
```

```bash
# Set API key
export OLLAMA_API_KEY=ollama-your-key

# Use Ollama Cloud
CommitCraft --provider ollama_cloud
```

See the [Ollama Cloud Setup Guide](config.md#ollama-cloud-setup-guide) for details.

#### 2. Named Provider Profiles

Configure multiple provider instances with different settings:

```toml
# Local Ollama
[models]
provider = "ollama"
model = "qwen3"

# Remote Ollama at work
[providers.work_ollama]
provider = "ollama"
model = "llama3"
host = "https://ollama.work.com"

# DeepSeek for important commits
[providers.deepseek]
provider = "openai_compatible"
model = "deepseek-chat"
host = "https://api.deepseek.com"
```

```bash
# Switch providers easily
CommitCraft --provider work_ollama
CommitCraft --provider deepseek
```

See [Named Provider Profiles](config.md#named-provider-profiles) for details.

#### 3. Interactive Git Hook Mode

Git hooks now prompt for CommitClues by default:

```bash
# Install interactive hook
CommitCraft hook

# Now when you commit:
git commit
# > What type of commit is this?
# > [b] Bug fix, [f] Feature, [d] Docs, [r] Refactor, [n] None
```

Opt out with `--no-interactive`:
```bash
CommitCraft hook --no-interactive
```

#### 4. Hook Version Checking

Hooks automatically detect when they're outdated:

```
⚠️  CommitCraft hook is outdated (hook: 0.9.0, installed: 1.0.0)
   Update with: CommitCraft hook
```

#### 5. Enhanced Configuration Wizard

The `CommitCraft config` command now supports:
- Adding/editing/deleting named provider profiles
- Model selection by index number
- Visual API key input (`***`)
- More intuitive workflow

#### 6. Debug Mode

Inspect prompts without calling the AI:

```bash
CommitCraft --debug-prompt
# Shows:
# - Full system prompt with context variables
# - User prompt with diff and clues
# - No API call made
```

#### 7. Thinking Tags Support

Models like DeepSeek R1 show reasoning process:

```bash
CommitCraft --show-thinking
# Displays <think>...</think> tags in output
```

#### 8. Improved Color Support

Colors now work correctly across all shells:
- Forced by default with `FORCE_COLOR=1`
- Disable with `--no-color` or `NO_COLOR=1`

---

## Configuration File Migration

### Step 1: Backup Your Existing Config

```bash
# Back up global config
cp ~/.config/commitcraft/config.toml ~/.config/commitcraft/config.toml.backup

# Back up project config
cp .commitcraft/config.toml .commitcraft/config.toml.backup
```

### Step 2: Update Provider Names

Find and replace in your config files:
```bash
# Linux/macOS
sed -i 's/custom_openai_compatible/openai_compatible/g' ~/.config/commitcraft/config.toml
sed -i 's/custom_openai_compatible/openai_compatible/g' .commitcraft/config.toml

# Or manually edit
```

### Step 3: Restructure Model Options (if needed)

If you had custom options outside standard ones, move them to `[models.options]`:

**Before:**
```toml
[models]
provider = "ollama"
model = "qwen3"
temperature = 0.7
num_ctx = 8192
custom_param = "value"
```

**After:**
```toml
[models]
provider = "ollama"
model = "qwen3"

[models.options]
temperature = 0.7
num_ctx = 8192
custom_param = "value"
```

### Step 4: Update Environment Variables

Rename named provider API keys:

**Before (`.env`):**
```bash
PROVIDER_LITELLM_API_KEY=xxx
PROVIDER_REMOTE_OLLAMA_API_KEY=xxx
```

**After (`.env`):**
```bash
LITELLM_API_KEY=xxx
REMOTE_OLLAMA_API_KEY=xxx
```

### Step 5: Test Your Configuration

```bash
# Test with debug mode (doesn't make API calls)
CommitCraft --debug-prompt

# Test with actual commit message generation
git add .
CommitCraft
```

---

## Git Hook Migration

If you're using git hooks, update them after upgrading:

### Local Hooks

```bash
# Reinstall to get latest hook script
CommitCraft hook

# Or for non-interactive
CommitCraft hook --no-interactive
```

### Global Hooks

```bash
# Reinstall global hook
CommitCraft hook --global

# Or for non-interactive
CommitCraft hook --global --no-interactive
```

### Manual Hook Updates

If you've customized your hook script:

1. Compare old and new hooks:
   ```bash
   # See your current hook
   cat .git/hooks/prepare-commit-msg

   # Install new hook to a temp location and compare
   CommitCraft hook
   ```

2. Merge your customizations into the new hook

3. Ensure executable:
   ```bash
   chmod +x .git/hooks/prepare-commit-msg
   ```

---

## Troubleshooting Migration Issues

### "Provider not found" Error

**Cause:** Still using old `custom_openai_compatible` name

**Fix:**
```bash
# Find old references
grep -r "custom_openai_compatible" ~/.config/commitcraft/ .commitcraft/

# Replace with openai_compatible
```

### Environment Variables Not Working

**Cause:** Named provider API keys using old format

**Fix:**
Check your variable names:
```bash
# Check current variables
printenv | grep API_KEY

# Should be NICKNAME_API_KEY, not PROVIDER_NICKNAME_API_KEY
```

### Hook Still Using Old Version

**Cause:** Hook script wasn't updated after upgrade

**Fix:**
```bash
# Check hook version
cat .git/hooks/prepare-commit-msg | grep VERSION

# Reinstall
CommitCraft hook
```

### Config File Not Being Read

**Cause:** Invalid TOML syntax after manual edits

**Fix:**
```bash
# Validate TOML syntax
python3 -c "import tomli; tomli.load(open('.commitcraft/config.toml', 'rb'))"

# Or use CommitCraft debug mode
CommitCraft --debug-prompt
```

---

## Rollback Instructions

If you encounter issues and need to rollback:

```bash
# Uninstall v1.0.0
pipx uninstall commitcraft

# Install specific older version
pipx install commitcraft==0.1.1

# Restore config backups
cp ~/.config/commitcraft/config.toml.backup ~/.config/commitcraft/config.toml
cp .commitcraft/config.toml.backup .commitcraft/config.toml

# Reinstall hooks with old version
CommitCraft hook
```

Then report the issue at [GitHub Issues](https://github.com/Felix-Pedro/CommitCraft/issues) so we can help!

---

## Getting Help

If you need assistance with migration:

1. Check the [Troubleshooting Guide](troubleshooting.md)
2. Review the [Configuration Documentation](config.md)
3. Open an issue at [github.com/Felix-Pedro/CommitCraft/issues](https://github.com/Felix-Pedro/CommitCraft/issues)
4. Include:
   - CommitCraft version (`CommitCraft --version`)
   - Your config file (redact API keys!)
   - Error messages
   - Steps to reproduce
