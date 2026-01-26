#!/bin/zsh
# asciinema automation script for CommitCraft demo
# Record with: asciinema rec -c "./demo.sh" commitcraft-demo.cast
source ~/.config/zsh/zshrc
set -e

# Configuration
export PS1="\[\e[36m\]demo\[\e[0m\]$ "
DELAY_SHORT=0.5
DELAY_MEDIUM=0.7
DELAY_LONG=1.5
TYPING_SPEED=0.037  # Mean typing speed (Gaussian distribution)

# Helper function to simulate typing with Gaussian-distributed random delays
type_text() {
    text="$1"
    python3 demo_helper.py type "$text" $TYPING_SPEED
}

# Helper function to pause
pause() {
    sleep "${1:-$DELAY_MEDIUM}"
}

# Clear screen and show title
clear
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║              CommitCraft Demo                              ║"
echo "║        AI-Powered Git Commit Messages                      ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo
pause $DELAY_SHORT

# Introduction
echo "CommitCraft generates meaningful commit messages using LLMs"
echo "Let's start with installation and setup!"
echo
pause $DELAY_LONG

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Installation with uv"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Install CommitCraft as a global tool:"
pause $DELAY_SHORT
type_text "uv tool install commitcraft"
echo "  ✓ CommitCraft installed and available globally"
pause $DELAY_LONG
clear

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. Interactive Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "CommitCraft provides an interactive setup wizard:"
pause $DELAY_SHORT
type_text "CommitCraft config --help"
CommitCraft config --help
pause $DELAY_SHORT
echo
echo "This creates configuration files in .commitcraft/ or ~/.config/commitcraft/"
pause $DELAY_MEDIUM
clear

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. Project Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
pause $DELAY_SHORT
type_text "cat .commitcraft/config.toml"
bat --style=plain --paging=never --color auto config.example.toml
pause $DELAY_LONG
clear

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. Dry-Run Mode - Check token usage without API calls"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
pause $DELAY_SHORT
echo "Let's see what would be sent to the LLM:"
pause $DELAY_SHORT
type_text "CommitCraft --dry-run"
COMMITCRAFT_HOST="https://ollama.mydomain" CommitCraft --dry-run #2>&1 || true
pause $DELAY_LONG
clear

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. Multiple Provider Support"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "CommitCraft supports multiple LLM providers:"
echo "  • Ollama (local models)"
echo "  • OpenAI (GPT-4, GPT-3.5)"
echo "  • Google Gemini"
echo "  • Groq"
echo "  • Anthropic Claude"
echo "  • OpenAI-compatible APIs (DeepSeek, LocalAI, etc.)"
echo
echo "Example usage with different providers:"
type_text "CommitCraft --provider ollama --model gemma2"
echo
type_text "CommitCraft --provider google --model gemini-3-pro-preview"
pause $DELAY_LONG
clear

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. CommitClues - Guide the AI with context"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Help the AI understand your commit by providing hints:"
pause $DELAY_SHORT
echo
type_text "# Bug fix with description"
type_text "CommitCraft --bug  / CommitCraft --bug-desc 'Fixed null pointer in auth'"
echo
pause $DELAY_SHORT
type_text "# New feature"
type_text "CommitCraft --feat / CommitCraft --feat-desc 'Added dark mode support'"
echo
echo -e " \e[33m--refact\e[0m and \e[33m--docs\e[0m are also available or you can give out custom clue with \e[33m--context-clue\e[0m"
echo
pause $DELAY_LONG
clear

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6. Git Hook Integration - Automatic commit messages"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Install a git hook to automatically generate commit messages:"
pause $DELAY_SHORT
echo
type_text "# Install in current repository (interactive mode)"
type_text "CommitCraft hook"
echo
pause $DELAY_SHORT
type_text "# Install globally for all repositories"
type_text "CommitCraft hook --global"
echo
pause $DELAY_SHORT
type_text "# Install without interactive prompts"
type_text "CommitCraft hook --no-interactive"
echo
pause $DELAY_SHORT
echo "Once installed, every 'git commit' will:"
echo "  1. Prompt for commit type (bug/feature/docs/refactor)"
echo "  2. Call CommitCraft to generate an AI message"
echo "  3. Open your editor with the AI-generated message pre-filled"
echo "  4. You can edit, accept, or reject the message"
pause $DELAY_LONG
clear

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7. Two-Step Confirmation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Review settings before making API calls:"
pause $DELAY_SHORT
type_text "COMMITCRAFT_PROVIDER=google COMMITCRAFT_MODEL=gemini-2.5-flash-lite \ "
type_text "CommitCraft --confirm"
echo

# Run with confirmation mode if there are staged changes
if ! git diff --staged --quiet; then
    #echo "Let's see the confirmation in action:"
    #pause $DELAY_SHORT
    echo "... google and anthropic takes a litte longer to count tokens as they need an api call (free of cost)"
    (sleep 3 && echo "y") | COMMITCRAFT_PROVIDER=google COMMITCRAFT_MODEL=gemini-2.5-flash-lite uv run CommitCraft --confirm  --context-clue "just enter the hitchiker vibe and make a message about the joke in the file as serious developments"|| true
    echo
    pause $DELAY_SHORT

else
    echo "What you'll see:"
    echo "  1. Dry-run statistics (token count, context size, etc.)"
    echo "  2. Provider and model configuration"
    echo "  3. Prompt: 'Proceed with commit message generation? [Y/n]:'"
    echo "  4. If you press Enter or 'y', it generates the message"
    echo "  5. If you press 'n', it exits without calling the LLM"
    echo
    echo "This is useful in git hooks to review settings before API calls!"
fi

pause $DELAY_LONG
clear

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "8. Real Example - Git Hook in Action"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "Let's demonstrate the git hook workflow with current changes:"
pause $DELAY_SHORT
echo

# Ensure we have staged changes
if git diff --staged --quiet; then
    echo "No staged changes found."
    echo
fi

echo "Now let's commit using the git hook:"
echo "The hook will:"
echo "  1. Prompt for commit type (press Enter to skip) (if interactive mode is on)"
echo "  2. Generate the AI commit message"
echo "  3. Open editor with the message pre-filled"
echo
pause $DELAY_LONG

# Unset COMMITCRAFT_SKIP to enable the hook for this commit
unset COMMITCRAFT_SKIP

type_text "git commit"
echo
pause $DELAY_SHORT

# Actually run git commit to demonstrate the hook
# Note: This will be interactive - the user will:
# 1. Press Enter at the commit type menu
# 2. Wait for CommitCraft to generate the message
# 3. Press Ctrl+Q in micro to save and exit

COMMITCRAFT_PROVIDER=google COMMITCRAFT_MODEL=gemini-2.5-flash COMMITCRAFT_CLUE="just enter the hitchiker vibe and make a message about the jokes in the file as serious developments" git commit

echo
pause $DELAY_LONG
clear

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "9. Environment Variables - Override defaults"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "You can override configuration using environment variables:"
pause $DELAY_SHORT
echo
type_text "# Override provider and model"
type_text "export COMMITCRAFT_PROVIDER=openai"
type_text "export COMMITCRAFT_MODEL=gpt-4"
echo
pause $DELAY_SHORT
type_text "# Enable confirmation mode by default"
type_text "export COMMITCRAFT_CONFIRM=1"
echo
pause $DELAY_SHORT
type_text "# Skip hook for one commit"
type_text "COMMITCRAFT_SKIP=1 git commit"
echo
pause $DELAY_SHORT
type_text CommitCraft envvars
CommitCraft envvars
pause $DELAY_MEDIUM
echo "All variables can be set before the commit command for hook users!"
pause $DELAY_LONG
pause $DELAY_LONG

# Closing
clear
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║              Thank you for watching!                       ║"
echo "║                                                            ║"
echo "║  CommitCraft - AI-Powered Git Commit Messages              ║"
echo "║                                                            ║"
echo "║  Installation:                                             ║"
echo "║    uv tool install commitcraft                             ║"
echo "║    pipx install commitcraft                                ║"
echo "║    pip install commitcraft                                 ║"
echo "║                                                            ║"
echo "║  Source Code:                                              ║"
echo "║    https://github.com/Felix-Pedro/CommitCraft              ║"
echo "║                                                            ║"
echo "║  Documentation:                                            ║"
echo "║    https://felix-pedro.github.io/CommitCraft/              ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo
pause $DELAY_LONG
