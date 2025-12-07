# Troubleshooting

Common issues and solutions for CommitCraft.

## Common Issues

### "Ollama connection refused"
**Error:** `Connection refused` or `Max retries exceeded with url` when using `provider="ollama"`.

**Solution:**
1. Ensure Ollama is running (`ollama serve`).
2. Check if the host is correct (default: `http://localhost:11434`).
3. If running inside Docker/WSL, you might need to set `OLLAMA_HOST` to `http://host.docker.internal:11434`.

### "Model not found"
**Error:** The provider returns a 404 or "model not found" error.

**Solution:**
1. **Ollama:** Run `ollama pull <model_name>` to ensure the model is downloaded locally.
2. **OpenAI/Groq/Google:** Verify the model name is correct (e.g., `gpt-4`, `llama3-70b-8192`). Check the provider's documentation for the latest model IDs.

### "API Key not found"
**Error:** `ValueError: API Key is missing`

**Solution:**
1. Check your environment variables (`printenv | grep API_KEY`).
2. Ensure you have a `.env` file in the directory where you run CommitCraft.
3. If using a named provider profile, ensure the variable matches the pattern `NICKNAME_API_KEY`.

### Git Hook Not Triggering
**Issue:** You run `git commit` but CommitCraft doesn't start.

**Solution:**
1. Check if the hook exists: `ls -l .git/hooks/prepare-commit-msg`.
2. Ensure it is executable: `chmod +x .git/hooks/prepare-commit-msg`.
3. If you are using a GUI git client (VS Code, Sourcetree), ensuring `commitcraft` is in your system PATH is crucial. Try installing with `pipx ensurepath`.

### Missing Model Error (OpenAI-Compatible)
**Error:** `MissingModelError: The model cannot be None for the 'openai_compatible' provider`

**Solution:**
When using `openai_compatible` provider, you **must** specify both `--model` and `--host`:
```bash
CommitCraft --provider openai_compatible --model deepseek-chat --host https://api.deepseek.com
```

Or in config:
```toml
[models]
provider = "openai_compatible"
model = "deepseek-chat"
host = "https://api.deepseek.com"
```

### Missing Host Error (OpenAI-Compatible)
**Error:** `MissingHostError: The 'host' field is required and must be a valid URL when using the 'openai_compatible' provider`

**Solution:**
The `openai_compatible` provider requires a host URL:
```bash
CommitCraft --provider openai_compatible --model your-model --host https://your-api-endpoint.com
```

### Diff Too Large / Token Limit Exceeded
**Error:** `context_length_exceeded` or similar token limit errors

**Solution:**
1. Use `.commitcraft/.ignore` to exclude large generated files, lock files, or build artifacts
2. For Ollama, increase `num_ctx`:
   ```bash
   CommitCraft --num-ctx 32768
   ```
3. Commit smaller, more focused changesets
4. Use `--ignore` to temporarily exclude files:
   ```bash
   CommitCraft --ignore "package-lock.json,dist/*"
   ```

### Hook Permission Denied (macOS/Linux)
**Error:** `Permission denied: .git/hooks/prepare-commit-msg`

**Solution:**
```bash
chmod +x .git/hooks/prepare-commit-msg
```

If you still have issues, check if your system prevents hook execution. On macOS, you may need to allow the script in System Preferences > Security & Privacy.

### Hook Not Running in GUI Clients
**Issue:** Hook works in terminal but not in VS Code, Sourcetree, or other GUI clients

**Solution:**
GUI clients may not have the same PATH as your terminal. Ensure `commitcraft` is in a standard location:

```bash
# Check where commitcraft is installed
which commitcraft

# Ensure pipx bin directory is in PATH
pipx ensurepath

# Restart your GUI client
```

Alternatively, modify the hook to use the full path to commitcraft:
```bash
# In .git/hooks/prepare-commit-msg
/home/youruser/.local/bin/commitcraft --bug-desc "..." || exit 0
```

### Configuration File Not Found
**Issue:** CommitCraft doesn't recognize your config file

**Solution:**
1. Check file location:
   - Project: `.commitcraft/config.toml` (in repo root)
   - Global: `~/.config/commitcraft/config.toml` (Linux/macOS) or `%APPDATA%\commitcraft\config.toml` (Windows)
2. Verify file format is valid TOML/YAML/JSON
3. Use `--config-file` to specify custom location:
   ```bash
   CommitCraft --config-file /path/to/config.toml
   ```

### Unauthorized / 401 Error (Ollama Cloud)
**Error:** `401 Unauthorized` when using `ollama_cloud`

**Solution:**
1. Verify your API key is correct
2. Check `OLLAMA_API_KEY` environment variable is set:
   ```bash
   echo $OLLAMA_API_KEY
   ```
3. Regenerate your API key at [ollama.com/settings/keys](https://ollama.com/settings/keys)
4. Ensure no extra whitespace in the API key

### Wrong Model Output Format
**Issue:** Model outputs in unexpected format or includes thinking tags you don't want to see

**Solution:**
- To hide thinking tags: Don't use `--show-thinking` flag (default behavior)
- To see thinking tags: Use `--show-thinking`
- Check if you're using the right model for your task (some models are more verbose than others)

### Colors Not Showing / Broken in Terminal
**Issue:** Output lacks colors or shows broken color codes

**Solution:**
1. CommitCraft forces colors by default. If you see broken codes, your terminal might not support ANSI colors.
2. Disable colors:
   ```bash
   CommitCraft --no-color
   # or
   NO_COLOR=1 CommitCraft
   ```
3. For zsh users: Colors should work by default due to `FORCE_COLOR=1`

### Named Provider Not Found
**Error:** `ValueError: Provider 'my_provider' not found`

**Solution:**
1. Ensure the provider is defined in config:
   ```toml
   [providers.my_provider]
   provider = "ollama"
   model = "qwen3"
   ```
2. Use the exact nickname with `--provider`:
   ```bash
   CommitCraft --provider my_provider
   ```
3. Provider nicknames are case-sensitive

### Temperature/Options Not Working
**Issue:** Setting `temperature` or other options has no effect

**Solution:**
Different providers support different options. Check the [Provider-Specific Options](cli.md#provider-specific-options-support) table:
- `num_ctx` only works with **local Ollama**
- Ollama Cloud doesn't support `num_ctx`
- Google uses `max_output_tokens` instead of `max_tokens` (CommitCraft handles this automatically)

### Jinja2 Template Errors
**Error:** `jinja2.exceptions.TemplateSyntaxError`

**Solution:**
Check your custom `system_prompt` for valid Jinja2 syntax:
```toml
# Bad
system_prompt = "Project: {{ project_name }"  # Missing closing braces

# Good
system_prompt = "Project: {{ project_name }}"
```

### Environment Variables Not Loading
**Issue:** Env vars in `.env` file aren't being used

**Solution:**
1. Ensure `.env` file is in the directory where you run CommitCraft
2. Alternatively, use `CommitCraft.env` (CommitCraft-specific)
3. Check file permissions (must be readable)
4. Verify no typos in variable names
5. For named providers, use `NICKNAME_API_KEY` (uppercase)

## FAQ

### How does CommitCraft handle large diffs?
CommitCraft automatically calculates the required context size for Ollama. For other providers, it respects the model's token limits. If a diff is too large, it might be truncated. You can use `--ignore` to exclude lockfiles or generated files to reduce the diff size.

### Can I use this with a private LLM?
Yes! Use the `openai_compatible` provider. You can point it to any endpoint (LM Studio, LocalAI, vLLM) that supports the OpenAI chat completions API format.

### Does it send my code to the cloud?
*   **Ollama (Local):** No. Everything runs on your machine.
*   **Commercial Providers (OpenAI, Groq, etc.):** Yes, the diff is sent to their API. Check their privacy policies.
