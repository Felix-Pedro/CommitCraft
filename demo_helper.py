#!/usr/bin/env python3
"""
Helper script for demo.sh to provide:
1. Gaussian-distributed typing delays
2. Automated responses to interactive prompts
"""

import sys
import time
import random
import subprocess
import select


def get_gaussian_delay(mean: float, stddev: float | None = None) -> float:
    """
    Generate a typing delay using Gaussian distribution.

    Args:
        mean: Mean typing speed in seconds
        stddev: Standard deviation (defaults to mean/3 for natural variation)

    Returns:
        Delay in seconds, clamped to reasonable bounds
    """
    if stddev is None:
        stddev = mean / 3.0

    delay = random.gauss(mean, stddev)
    # Clamp to avoid negative or extremely long delays
    return max(0.01, min(delay, mean * 3))


def type_text(text: str, mean_speed: float = 0.05, colorize: bool = True):
    """
    Type text with gaussian-distributed random delays and optional zsh-like syntax coloring.

    Args:
        text: Text to type
        mean_speed: Mean typing speed in seconds per character
        colorize: Apply zsh-like syntax highlighting for commands
    """
    # ANSI color codes for zsh-like syntax highlighting
    RESET = "\033[0m"
    COMMAND_COLOR = "\033[32m"  # Green for valid commands
    ARG_COLOR = "\033[36m"  # Cyan for arguments
    FLAG_COLOR = "\033[33m"  # Yellow for flags
    STRING_COLOR = "\033[35m"  # Magenta for strings
    COMMENT_COLOR = "\033[90m"  # Gray for comments

    if not colorize:
        for char in text:
            sys.stdout.write(char)
            sys.stdout.flush()
            time.sleep(get_gaussian_delay(mean_speed))
        sys.stdout.write("\n")
        sys.stdout.flush()
        return

    # Simple tokenizer for syntax highlighting
    tokens = []
    current_token = ""
    in_string = False
    string_char = None

    i = 0
    while i < len(text):
        char = text[i]

        # Handle strings
        if char in ('"', "'") and (i == 0 or text[i - 1] != "\\"):
            if not in_string:
                if current_token:
                    tokens.append(("token", current_token))
                    current_token = ""
                in_string = True
                string_char = char
                current_token = char
            elif char == string_char:
                current_token += char
                tokens.append(("string", current_token))
                current_token = ""
                in_string = False
                string_char = None
            else:
                current_token += char
        elif in_string:
            current_token += char
        elif char == "#":
            # Comment - rest of line
            if current_token:
                tokens.append(("token", current_token))
            tokens.append(("comment", text[i:]))
            break
        elif char in (" ", "\t"):
            if current_token:
                tokens.append(("token", current_token))
                current_token = ""
            tokens.append(("space", char))
        else:
            current_token += char

        i += 1

    if current_token:
        if in_string:
            tokens.append(("string", current_token))
        else:
            tokens.append(("token", current_token))

    # Colorize and type tokens
    is_first_token = True
    for token_type, token_value in tokens:
        if token_type == "space":
            sys.stdout.write(token_value)
            sys.stdout.flush()
            time.sleep(get_gaussian_delay(mean_speed))
        elif token_type == "comment":
            # Comment in gray
            for char in COMMENT_COLOR + token_value + RESET:
                sys.stdout.write(char)
                sys.stdout.flush()
                if char not in (COMMENT_COLOR, RESET, "\033", "[", "0", "9", "m"):
                    time.sleep(get_gaussian_delay(mean_speed))
        elif token_type == "string":
            # Strings in magenta
            for char in STRING_COLOR + token_value + RESET:
                sys.stdout.write(char)
                sys.stdout.flush()
                if char not in (STRING_COLOR, RESET, "\033", "[", "0", "3", "5", "m"):
                    time.sleep(get_gaussian_delay(mean_speed))
        elif token_type == "token":
            # Determine color based on position and content
            if is_first_token:
                # First token is the command - green
                color = COMMAND_COLOR
                is_first_token = False
            elif token_value.startswith("-"):
                # Flags in yellow
                color = FLAG_COLOR
            else:
                # Arguments in cyan
                color = ARG_COLOR

            for char in color + token_value + RESET:
                sys.stdout.write(char)
                sys.stdout.flush()
                if char not in (
                    color,
                    RESET,
                    "\033",
                    "[",
                    "0",
                    "1",
                    "2",
                    "3",
                    "6",
                    "m",
                ):
                    time.sleep(get_gaussian_delay(mean_speed))

    sys.stdout.write("\n")
    sys.stdout.flush()


def run_with_responses(command: list, responses: dict | None = None):
    """
    Run a command and automatically respond to prompts.

    Args:
        command: Command as list of strings
        responses: Dict mapping prompt keywords to responses

    Example responses dict:
    {
        "Continue?": "y\n",
        "Enter choice": "1\n",
        "Skip": "n\n"
    }
    """
    if responses is None:
        responses = {}

    # Start the process
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1,
    )

    output_buffer = ""

    try:
        while True:
            # Check if process has finished
            if process.poll() is not None:
                # Read any remaining output
                if process.stdout:
                    remaining = process.stdout.read()
                    if remaining:
                        print(remaining, end="", flush=True)
                break

            # Read output with timeout
            if process.stdout:
                ready, _, _ = select.select([process.stdout], [], [], 0.1)

                if ready:
                    char = process.stdout.read(1)
                    if not char:
                        break

                    print(char, end="", flush=True)
                    output_buffer += char

                    # Check if we need to respond to a prompt
                    for keyword, response in responses.items():
                        if keyword.lower() in output_buffer.lower():
                            # Wait a moment to simulate user thinking
                            time.sleep(0.5)
                            if process.stdin:
                                process.stdin.write(response)
                                process.stdin.flush()
                            # Clear buffer after responding
                            output_buffer = ""
                            break

            # Read output with timeout
            ready, _, _ = select.select([process.stdout], [], [], 0.1)

            if ready:
                char = process.stdout.read(1)
                if not char:
                    break

                print(char, end="", flush=True)
                output_buffer += char

                # Check if we need to respond to a prompt
                for keyword, response in responses.items():
                    if keyword.lower() in output_buffer.lower():
                        # Wait a moment to simulate user thinking
                        time.sleep(0.5)
                        process.stdin.write(response)
                        process.stdin.flush()
                        # Clear buffer after responding
                        output_buffer = ""
                        break

                # Keep buffer size manageable
                if len(output_buffer) > 500:
                    output_buffer = output_buffer[-500:]

    except KeyboardInterrupt:
        process.terminate()
        raise
    finally:
        process.wait()

    return process.returncode


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print(f"  {sys.argv[0]} type <text> [mean_speed]")
        print(f"  {sys.argv[0]} run <command> [keyword:response ...]")
        sys.exit(1)

    mode = sys.argv[1]

    if mode == "type":
        # Type text with gaussian delays
        if len(sys.argv) < 3:
            print("Error: text required")
            sys.exit(1)

        text = sys.argv[2]
        mean_speed = float(sys.argv[3]) if len(sys.argv) > 3 else 0.05
        type_text(text, mean_speed)

    elif mode == "run":
        # Run command with automated responses
        if len(sys.argv) < 3:
            print("Error: command required")
            sys.exit(1)

        # Parse command (everything until we hit keyword:response pairs)
        command_parts = []
        responses = {}
        i = 2

        while i < len(sys.argv):
            arg = sys.argv[i]
            if ":" in arg and "=" not in arg:  # Response mapping
                keyword, response = arg.split(":", 1)
                # Unescape response
                response = response.replace("\\n", "\n").replace("\\t", "\t")
                responses[keyword] = response
            else:
                command_parts.append(arg)
            i += 1

        exit_code = run_with_responses(command_parts, responses)
        sys.exit(exit_code)

    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)
