 # CommitCraft

CommitCraft is a tool designed to enhance your commit messages by leveraging Large Language Models (LLMs). It provides an intuitive interface that simplifies the process of generating better, more informative commit messages based on staged changes in your git repository.

## Features

- **Provider Agnostic**: Supports multiple LLM providers including Ollama, Google, OpenAI, and Any OpenAI compatible endpoint.
- **Configurable Context Size**: Automatically adjusts the context size for optimal performance. (Ollama only)
- **Emoji Support**: Option to include emojis in your commit messages based on predefined conventions. Pre-configured witch gitmoji specification.
- **User-Friendly CLI**: A command-line interface allows users to easily specify provider, model, and other settings.

## Installation

You can install CommitCraft using `pipx` for a hassle-free experience:

```bash
pipx install commitcraft
```

If you intent to use some provider other than ollama consider using one of the folowing:

```bash
pipx install commitcraft[openai]
```

```bash
pipx install commitcraft[groq]
```

```bash
pipx install commitcraft[google]
```

```bash
pipx install commitcraft[all-providers]
```


## Configuration

CommitCraft can be configured via either command-line arguments or through configuration files located in the `.commitcraft` directory. Supported file types are TOML, YAML, and JSON. The default locations for these files are:

- `context`: `./.commitcraft/context.{toml|yaml|json}`
- `models`: `./.commitcraft/models.{toml|yaml|json}`
- `emoji`: `./.commitcraft/emoji.{toml|yaml|json}`
- `config`: `./.commitcraft/config.{toml|yaml|json}`

Alternatively, you can specify a configuration file path using the `--config-file` argument.

Your API keys shall be stored in enviroment variables or in a `.env` file

## Usage

To use CommitCraft, simply run:

```bash
CommitCraft
```

If no arguments are provided, then the configuration files (if present) will be used to determine settings such as provider, model, and other options. If there are no configuration files, the tool will fall back to using default settings (ollama, gemma2).

The diff used by CommitCraft is the result of `git diff --staged -M` so you will need to add files you want to consider before using it.

You may pipe the output to other commands.

### Command-Line Arguments

- `--provider`: Specifies the LLM provider (e.g., `ollama`, `google`, `openai`, `custom_openai_compatible`).
- `--model`: The name of the model to use.
- `--config-file`: Path to a configuration file.
- `--system-prompt`: A system prompt to guide the LLM.
- `--num-ctx`: Context size for the model.
- `--temperature`: Temperature setting for the model.
- `--max-tokens`: Maximum number of tokens for the model.
- `--host`: HTTP or HTTPS host for the provider, required for `custom_openai_compatible`.

### Example Configuration File

Here's an example configuration file in TOML format:

```toml
[context]
project_name = "MyProject"
project_language = "Python"
project_description = "A project to enhance commit messages."
commit_guidelines = "Ensure each commit is concise and describes the changes clearly."

[models]
provider = "ollama"
model = "gemma2"
system_prompt = "You are a helpful assistant for generating commit messages based on git diff."
options = {num_ctx = 8192, temperature = 0.7}

[emoji]
emoji_steps = "single"
emoji_convention = "simple"
```

## Privacy

CommitCraft itself does not log, record or send any information about your usage and project, or any other info. 

However, it is important to note that by using CommitCraft, you are agreeing to the terms of the providers you choose, as CommitCraft sends diffs and contextual information to their API. Unless you self-host the application, these providers may still collect your request history and metadata information. For more detailed information about how each provider handles your data, please review their respective privacy policies:

- [Groq](https://groq.com/privacy-policy/)
- [Google](https://ai.google.dev/gemini-api/terms)
- [OpenAI](https://openai.com/policies/privacy-policy/)

## Princing

CommitCraft is Free Software in this case free as in freedom and as in no price atached.

But, similar to privacy concerns, if you are not self-hosting your models, it's important to be aware of the pricing structure for the providers you use. As of now, Groq and Google provide a free tier, while OpenAI operates on a fully usage-based pricing model. For more detailed information about pricing options, please refer to the documentation provided by each provider:

- [Groq](https://groq.com/pricing/)
- [Google](https://ai.google.dev/pricing)
- [OpenAI](https://openai.com/api/pricing/)


## License

This project is licensed under the AGPL 3.0 License - see the [LICENSE](LICENSE) file for details.

---

Thank you for using CommitCraft! We hope this tool helps you craft better commit messages effortlessly.