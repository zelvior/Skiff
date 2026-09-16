```
███████╗ ██╗  ██╗ ██╗ ███████╗ ███████╗
██╔════╝ ██║ ██╔╝ ██║ ██╔════╝ ██╔════╝
███████╗ █████╔╝  ██║ █████╗   █████╗  
╚════██║ ██╔═██╗  ██║ ██╔══╝   ██╔══╝  
███████║ ██║  ██╗ ██║ ██║      ██║     
╚══════╝ ╚═╝  ╚═╝ ╚═╝ ╚═╝      ╚═╝     
```

# Skiff - BYOK AI Coding Agent CLI

**A high-performance BYOK AI coding agent CLI built to run everywhere — from Windows XP 32-bit to Windows 11 64-bit, as well as Linux and macOS — as a single dependency-free Python file.**

Version 1.0.0

---

## Table of Contents
1. [Philosophy & Architecture](#philosophy--architecture)
2. [Platform & OS Compatibility Matrix](#platform--os-compatibility-matrix)
3. [Features Overview](#features-overview)
4. [Installation & Requirements](#installation--requirements)
5. [Quick Start](#quick-start)
6. [Command-Line Interface (CLI) Reference](#command-line-interface-cli-reference)
7. [The Terminal UI (TUI) & Slash Commands](#the-terminal-ui-tui--slash-commands)
8. [Providers & BYOK Management](#providers--byok-management)
9. [Complete Tool Specifications](#complete-tool-specifications)
10. [Ambient Context & Plugin System](#ambient-context--plugin-system)
11. [Configuration & Safety Model](#configuration--safety-model)
12. [Testing & Quality Assurance](#testing--quality-assurance)

---

## Philosophy & Architecture

Skiff was created to deliver an autonomous AI coding experience across all desktop operating systems without installation friction or heavy package manager overhead:

- **100% Stdlib-Only:** Zero external Python dependencies (`pip install` free). Uses standard library modules (`urllib`, `ssl`, `json`, `ast`, `subprocess`, `hashlib`, `fnmatch`).
- **Python 2.7 to 3.x Compatibility:** Polyglot syntax supported on legacy Python 2.7 (Windows XP) through modern Python 3.12+ (Windows 11 / modern Unix).
- **ANSI Terminal Awareness:** Automatically queries terminal capability (e.g. Windows 10 build 10586+ VT mode or POSIX shell). Enables ANSI colors and borders on supporting terminals while cleanly degrading to plain text on older consoles (cp437 / cp1252 on Win XP/7/8).
- **Self-Healing Loop:** Automatically captures build and test execution output. On failure, the agent reads errors, patches the code, and re-runs up to 3 times automatically.
- **Data Preservation:** Every file write, patch, or deletion triggers a snapshot backup into `~/.skiff/backups/`.

---

## Platform & OS Compatibility Matrix

| OS / Platform | Architecture | Python Versions | ANSI Support | Status |
|---|---|---|---|---|
| Windows XP / Vista / 7 / 8 | 32-bit / 64-bit | 2.7.x - 3.4.x | Plain Text Fallback | Fully Supported |
| Windows 10 / 11 / Windows Terminal | 32-bit / 64-bit / ARM64 | 3.6 - 3.12+ | Full ANSI Color & Boxes | Fully Supported |
| Linux (Ubuntu, Debian, Fedora, Arch, RHEL) | x86, x86_64, ARM64 | 2.7.x / 3.x | Full ANSI Color & Boxes | Fully Supported |
| macOS (Intel & Apple Silicon) | x86_64, arm64 | 2.7.x / 3.x | Full ANSI Color & Boxes | Fully Supported |

---

## Features Overview

- **Multi-Provider BYOK Engine:** Native integrations for OpenAI, Anthropic Claude, OpenRouter, Groq, local Ollama servers, and offline local GGUF execution via the `ollama` CLI.
- **TUI & Status Bar:** Header displays active AI provider, model, API key state, current working directory, and active git branch.
- **Interactive Slash Commands:** `/clear`, `/history`, `/config`, `/help`, `/plan`, `/menu`, and `/exit` available during interactive chat.
- **21 Built-In Agent Tools:** `read_file`, `write_file`, `append_file`, `patch_file`, `list_dir`, `find_files`, `file_info`, `search_files`, `delete_path`, `make_dir`, `run_command`, `index_code`, `map_repo`, `git_diff`, `git_status`, `git_commit`, `git_log`, `platform_info`, `run_tests`, `mcp_call`, `plan`.
- **Extensible Plugin Architecture:** Auto-loads custom Python tool definitions placed in `~/.skiff/plugins/*.py`.
- **Ambient Project Awareness:** Auto-reads instructions from `CLAUDE.md`, `.cursorrules`, `.github/copilot-instructions.md`, `opencode.json`, and `AGENTS.md`.

---

## Installation & Requirements

No installation or package manager required.

**Prerequisites:** Python 2.7 or Python 3.x installed on system PATH.

```bash
# Clone or download repository
git clone https://github.com/zelvior/Skiff.git
cd Skiff

# Run directly
python skiff.py
```

On Windows environments, `skiff.bat` is included as a double-clickable launcher.

---

## Quick Start

```bash
python skiff.py               # Launch menu TUI
python skiff.py chat          # Launch interactive chat session
python skiff.py run "task"    # Execute a single task and exit
```

---

## Command-Line Interface (CLI) Reference

| Command | Arguments | Description |
|---|---|---|
| `skiff` | None | Launches the interactive TUI menu |
| `skiff setup` | None | Runs the interactive provider & API key wizard |
| `skiff chat` | None | Starts an interactive agent chat session |
| `skiff run` | `"<task>"` | Runs a specific agent task and exits |
| `skiff config` | None | Displays active configuration with API key masked |
| `skiff config export` | `<file.json>` | Exports configuration to JSON with API key redacted |
| `skiff config import` | `<file.json>` | Imports configuration settings from JSON |
| `skiff usage` | None | Shows cumulative token usage and estimated USD cost |
| `skiff history` | None | Lists previous agent sessions |
| `skiff --version` | None | Prints version information |
| `skiff <task>` | `<anything>` | Fallback: treats unrecognized CLI input directly as a task |

---

## The Terminal UI (TUI) & Slash Commands

### TUI Menu Options
- **`[1]` Chat with Skiff:** Starts an interactive chat session.
- **`[2]` Run a single task:** Prompt for a single task execution.
- **`[3]` Setup / change API key & model:** Re-run provider wizard.
- **`[4]` Show config:** Inspect settings.
- **`[5]` Help:** View built-in guidance.
- **`[6]` Token usage & cost monitor:** View session token counters and USD cost.
- **`[7]` Custom system instructions:** Define persistent extra agent instructions.
- **`[8]` Session history / replay:** Replay past transcripts.
- **`[9]` MCP servers:** Manage JSON-RPC Model Context Protocol servers.
- **`[P]` Plugins:** View loaded user plugins from `~/.skiff/plugins/`.
- **`[0]` Exit:** Quit Skiff.

### Interactive Slash Commands
While in interactive chat mode (`skiff chat` or Option 1), the following slash commands are available:
- `/clear` - Clears the terminal screen and redraws status header.
- `/history` - Lists recent session transcripts.
- `/config` - Prints active configuration.
- `/plan` - Displays the agent's last recorded multi-step execution plan.
- `/help` - Displays available slash commands.
- `/menu` - Returns to the main TUI menu.
- `/exit` - Exits Skiff.

---

## Providers & BYOK Management

Skiff does not bundle proprietary API keys. You bring your own key (BYOK):

| Provider | Default Model | Base Endpoint / Execution | Key Required |
|---|---|---|---|
| OpenAI | `gpt-4o-mini` | `https://api.openai.com/v1/chat/completions` | Yes |
| Anthropic | `claude-sonnet-4-6` | `https://api.anthropic.com/v1/messages` | Yes |
| OpenRouter | `openai/gpt-4o-mini` | `https://openrouter.ai/api/v1/chat/completions` | Yes |
| Groq | `llama-3.3-70b-versatile` | `https://api.groq.com/openai/v1/chat/completions` | Yes |
| Ollama | `llama3.1` | `http://localhost:11434/v1/chat/completions` | No |
| Local GGUF | `llama3.1` | Subprocess execution via `ollama run <model>` | No |
| Custom | User Defined | User Defined OpenAI-compatible endpoint | Optional |

---

## Complete Tool Specifications

1. `read_file(path)`: Reads full text content from target file path.
2. `write_file(path, content)`: Overwrites target file path (creates backup first).
3. `append_file(path, content)`: Appends text content to file.
4. `patch_file(path, old_str, new_str)`: Surgically replaces exact substring matching in target file.
5. `list_dir(path)`: Lists directory contents with sizes and folder indicators.
6. `find_files(path, glob_pattern)`: Finds files matching wildcard pattern across directory hierarchy.
7. `file_info(path)`: Retrieves detailed file metadata (size, mode/permissions, modification time).
8. `search_files(path, pattern)`: Executes regex search across non-ignored files in target folder.
9. `delete_path(path)`: Deletes file or directory recursively (creates backup for files).
10. `make_dir(path)`: Recursively creates directory path.
11. `run_command(cmd)`: Shells out to execute system command, returning stdout/stderr and returncode.
12. `index_code(path)`: Parses Python AST to extract functions, classes, and import statements.
13. `map_repo(path)`: Generates repository file tree and AST summary respecting `.skiffignore`.
14. `git_diff()`: Executes `git diff` for repository.
15. `git_status()`: Executes `git status --porcelain`.
16. `git_commit(message)`: Stages all changes (`git add -A`) and commits with message.
17. `git_log(max_count)`: Views recent git commit history.
18. `platform_info()`: Diagnostics for OS, Python version, ANSI capabilities, and working folder.
19. `run_tests(cmd)`: Runs test suite command and captures output for self-healing loops.
20. `mcp_call(server, method, params)`: Dispatches JSON-RPC call to configured MCP server.
21. `plan(steps)`: Saves structured multi-step plan array before execution.

---

## Ambient Context & Plugin System

### Ambient Context
Skiff automatically inspects the current directory and merges instructions into system prompt from:
- `CLAUDE.md`
- `.cursorrules`
- `.github/copilot-instructions.md`
- `opencode.json`
- `AGENTS.md`

### Plugins
Drop any Python file into `~/.skiff/plugins/name.py` defining:
```python
TOOL_NAME = "custom_tool"
TOOL_DESC = "Tool description"

def run(args):
    return {"ok": True, "result": "output"}
```
It instantly registers as a callable agent tool.

---

## Configuration & Safety Model

All configuration and operational data persist under `~/.skiff/`:
- `config.json`: Persistent settings, token usage, USD cost tally.
- `history.json`: Stores last 50 session transcripts.
- `mcp.json`: MCP server endpoints.
- `backups/`: Reversible file backups generated prior to modification.
- `plugins/`: User-defined python tool plugins.

---

## Testing & Quality Assurance

Skiff includes a unit test suite verifying core mechanics:

```bash
python3 test_skiff.py
```
Tests cover JSON extraction, backup creation, AST indexing, file manipulation, TUI inputs, and plugin execution.
