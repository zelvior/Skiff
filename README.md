# Skiff

**A BYOK AI coding agent CLI, built to run everywhere — from Windows XP 32-bit to Windows 11 64-bit, and on Linux and macOS — as a single dependency-free Python file.**

Version 1.0.0

---

## Table of contents
1. [Philosophy](#philosophy)
2. [Features](#features)
3. [Installation](#installation)
4. [Quick start](#quick-start)
5. [Command-line reference](#command-line-reference)
6. [The TUI](#the-tui)
7. [Providers (BYOK)](#providers-byok)
8. [Agent tools](#agent-tools)
9. [Extensibility](#extensibility)
10. [Configuration & data files](#configuration--data-files)
11. [Safety model](#safety-model)
12. [Known scope boundaries](#known-scope-boundaries)

---

## Philosophy

Skiff exists to work identically everywhere, with nothing to install beyond a Python interpreter:

- **Stdlib-only.** No `pip install`, no third-party packages, no build step, ever. Every feature is implemented with what ships in the Python standard library.
- **No `curses`.** Curses isn't reliably available on stock Windows, so the TUI is hand-rolled with `input()`, `print()`, and `os.system("cls"/"clear")`.
- **ANSI color, only when it's real.** Skiff detects terminal capability at startup and only emits ANSI escape codes on terminals that support them (Windows 10+/Windows Terminal, or any Unix shell). Older Windows consoles (XP, 7, 8, early 10) get clean, uncorrupted plain text automatically.
- **One file, two Python generations.** The same `skiff.py` runs unmodified on Python 2.7 and Python 3.x.
- **Every feature must degrade gracefully on the oldest supported target before it ships.** That's the bar for anything added to this project.

## Features

| Category | What it does |
|---|---|
| BYOK API manager | Bring your own key for OpenAI-compatible APIs, Anthropic, OpenRouter, Groq, Ollama, or fully offline local GGUF models. Key auto-requested on first use; overridable per-run via the `SKIFF_API_KEY` environment variable. |
| Terminal UI | Menu-driven, breadcrumbed, color-coded plain-text TUI; falls back cleanly on non-ANSI terminals. |
| Shell execution engine | Runs POSIX or Win32 shell commands natively via `subprocess`, no shell-specific code paths to maintain. |
| File system abstraction | Cross-platform read / write / append / list / delete / mkdir / surgical patch, all path-normalized per OS. |
| Automatic backups | Every overwrite or delete of a file is snapshotted to `~/.skiff/backups` first — file operations are reversible. |
| AST code indexer | Parses Python files into functions / classes / imports using the stdlib `ast` module. |
| Repository mapper | Full directory tree + per-file AST index in one call, respecting a `.skiffignore` file (glob patterns, one per line). |
| Git integration | `git diff` / `git status` surfaced as agent tools. |
| Self-healing test loop | The agent can run a test command, read failures, patch the offending file, and re-run — looping until green or capped. |
| Multi-step planning | The agent records an explicit step list (`plan`) before executing non-trivial tasks. |
| Token usage & cost monitor | Tracks cumulative input/output tokens and estimates USD cost per session, persisted across runs. |
| MCP client | Calls JSON-RPC-based MCP servers configured in `~/.skiff/mcp.json`. |
| Session history & replay | Every session is persisted (last 50) and replayable in full from the TUI. |
| Custom system instructions | User-supplied text appended to the agent's system prompt, editable from the TUI. |
| Ambient project context | Auto-reads `CLAUDE.md`, `.cursorrules`, `.github/copilot-instructions.md`, `opencode.json`, and `AGENTS.md` from the working directory into context, so Skiff respects instructions already written for other AI coding tools. |
| Plugin tools | Drop a `.py` file into `~/.skiff/plugins/` to register a new agent-callable tool with no core edits. |
| Config export/import | Share or restore configuration (API key always redacted on export) as portable JSON. |
| HTTP resilience | Automatic retry with exponential backoff on transient provider errors (429/500/502/503/504). |

## Installation

Requires only Python (2.7+ or any 3.x) on the target machine — nothing else.

```bash
# Any OS
python skiff.py
```

On Windows, `skiff.bat` is provided as a double-clickable launcher.

## Quick start

```bash
python skiff.py              # opens the TUI menu
python skiff.py chat         # interactive agent chat
python skiff.py run "create a hello.py that prints hi"
```

The first time you chat or run a task, Skiff asks for your API key once (BYOK) and remembers it — no separate setup step is required, though `skiff setup` (or TUI option **3**) lets you change it anytime.

## Command-line reference

| Command | Description |
|---|---|
| `skiff` | Launch the TUI menu (default with no arguments) |
| `skiff setup` | Configure provider, API key, model |
| `skiff chat` | Interactive agent chat session |
| `skiff run "<task>"` | Run a single agent task and exit |
| `skiff config` | Show current config (API key masked) |
| `skiff config export <file>` | Export config (API key redacted) to JSON |
| `skiff config import <file>` | Import config from a JSON file |
| `skiff usage` | Show cumulative token usage & estimated cost |
| `skiff history` | List the most recent sessions |
| `skiff --version` | Print the current version |
| `skiff <anything else>` | Treated as a task and run directly — no subcommand required |

Environment: `SKIFF_API_KEY`, if set, overrides the saved key for that invocation only.

## The TUI

Running `skiff` with no arguments opens a numbered, breadcrumbed menu:

```
[1] Chat with Skiff (agent session)
[2] Run a single task
[3] Setup / change API key & model
[4] Show config
[5] Help
[6] Token usage & cost monitor
[7] Custom system instructions
[8] Session history / replay
[9] MCP servers
[P] Plugins
[0] Exit
```

Every screen shows a breadcrumb, validates input, and returns cleanly on Ctrl+C. Tool calls, results, and errors are color-coded when the terminal supports ANSI, and rendered as plain, aligned text when it doesn't.

## Providers (BYOK)

| Provider | Requires a key | Notes |
|---|---|---|
| OpenAI | Yes | Default `gpt-4o-mini` |
| Anthropic | Yes | Default `claude-sonnet-4-6` |
| OpenRouter | Yes | Any OpenRouter-hosted model |
| Groq | Yes | Default `llama-3.3-70b-versatile` |
| Ollama | No | Talks to a local Ollama server over HTTP |
| Local GGUF | No | Fully offline/air-gapped; shells out to the `ollama` CLI directly |
| Custom | Depends | Any OpenAI-compatible chat completions endpoint |

## Agent tools

The agent chooses from these on every turn:

```
read_file, write_file, append_file, patch_file, list_dir, delete_path,
make_dir, run_command, index_code, map_repo, git_diff, git_status,
run_tests, mcp_call, plan, final_answer
```

Plus any tools registered via the plugin system (see below).

## Extensibility

Two ways to add capability without touching `skiff.py`:

**Ambient project context** — place any of `CLAUDE.md`, `.cursorrules`, `.github/copilot-instructions.md`, `opencode.json`, or `AGENTS.md` in your project root, and Skiff folds it into the agent's system prompt automatically on every run in that directory.

**Plugin tools** — drop a `.py` file into `~/.skiff/plugins/` defining:

```python
TOOL_NAME = "my_tool"
TOOL_DESC = "One-line description"

def run(args):
    return {"ok": True, "result": "..."}
```

It becomes a callable agent tool on next launch. A working example ships at `sample_plugins/word_count.py`. TUI option **P** lists everything currently loaded.

## Configuration & data files

All state lives under `~/.skiff/`:

| Path | Contents |
|---|---|
| `config.json` | Provider, model, API key, token/cost totals, custom system prompt |
| `history.json` | Last 50 sessions, full transcripts |
| `mcp.json` | Configured MCP servers |
| `plugins/` | User-added tool plugins |
| `backups/` | Automatic pre-overwrite/delete file snapshots |
| `last_plan.json` | Most recent agent-recorded plan |

## Safety model

- Every `write_file`, `patch_file`, and `delete_path` call snapshots the previous file version to `~/.skiff/backups` first.
- API keys are never written to export files.
- The agent operates with the permissions of the user running Skiff — it has no sandboxing beyond your OS's own file/user permissions. Treat it the same way you'd treat any tool with shell access.

## Known scope boundaries

- **Native compiled binary (Rust/Go/C):** not implemented, and not planned as a bolt-on. A genuine native build is a separate rewrite of the whole engine in a different language and toolchain — it would be a distinct future project, not a feature added to this file.
- **Local GGUF inference:** Skiff doesn't embed an inference engine. Offline execution works by shelling out to an installed `ollama` binary; without it, offline mode has nothing to call.
