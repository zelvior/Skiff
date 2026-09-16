#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Skiff - BYOK AI Coding Agent CLI
Stdlib-only. Runs on Python 2.7 (Windows XP) through Python 3.x (Windows 11).
"""

import os
import sys
import json
import re
import shutil
import subprocess
import traceback
import ast
import time
import hashlib
import glob as _glob

PY2 = sys.version_info[0] == 2

if PY2:
    import urllib2 as _urlreq
    import ssl as _ssl
    input = raw_input  # noqa: F821
    text_type = unicode  # noqa: F821
else:
    import urllib.request as _urlreq
    import urllib.error as _urlerr
    import ssl as _ssl
    text_type = str

IS_WIN = sys.platform.startswith("win")


def _supports_ansi():
    if not IS_WIN:
        return True
    # Windows 10+ (build 10586+) and Windows Terminal support ANSI.
    # XP/7/8/early10 cmd.exe do not - fall back to plain text there.
    ver = sys.getwindowsversion() if hasattr(sys, "getwindowsversion") else None
    if ver is None:
        return False
    if ver[0] > 10:
        return True
    if ver[0] == 10 and ver[2] >= 10586:
        try:
            import ctypes
            k = ctypes.windll.kernel32
            h = k.GetStdHandle(-11)
            mode = ctypes.c_uint32()
            if k.GetConsoleMode(h, ctypes.byref(mode)):
                k.SetConsoleMode(h, mode.value | 0x0004)
            return True
        except Exception:
            return False
    return False


ANSI = _supports_ansi()
UNICODE_BOX = ANSI  # old cmd.exe (cp437/cp1252) mangles box-drawing chars


def clr(code):
    return ("\x1b[%sm" % code) if ANSI else ""


C_RESET = clr("0")
C_BOLD = clr("1")
C_CYAN = clr("36")
C_GREEN = clr("32")
C_YELLOW = clr("33")
C_RED = clr("31")
C_DIM = clr("2")
C_MAGENTA = clr("35")
C_BLUE = clr("34")
C_WHITE_BOLD = clr("1;37")

BOX = {"tl": "+", "tr": "+", "bl": "+", "br": "+", "h": "-", "v": "|", "lt": "+", "rt": "+"}


def clear_screen():
    os.system("cls" if IS_WIN else "clear")


def term_width():
    try:
        if not PY2:
            return shutil.get_terminal_size((70, 20)).columns
    except Exception:
        pass
    return 70


def safe_width(cap=78, floor=40):
    w = term_width()
    if w < floor:
        w = floor
    if w > cap:
        w = cap
    return w


def hr(width=None, char="-"):
    w = width or safe_width()
    print(C_DIM + (char * w) + C_RESET)


def box_top(width):
    print(BOX["tl"] + BOX["h"] * (width - 2) + BOX["tr"])


def box_bottom(width):
    print(BOX["bl"] + BOX["h"] * (width - 2) + BOX["br"])


def box_line(text, width=None, color="", center=False):
    w = (width or safe_width()) - 4
    if len(text) > w:
        text = text[:w - 3] + "..."
    inner = text.center(w) if center else text.ljust(w)
    print("%s %s%s%s %s" % (BOX["v"], color, inner, C_RESET if color else "", BOX["v"]))


def print_banner(breadcrumb=""):
    w = safe_width(60)
    clear_screen()
    print(C_CYAN + C_BOLD)
    box_top(w)
    box_line("S K I F F", w, center=True)
    box_line("BYOK AI Coding Agent", w, center=True)
    box_bottom(w)
    print(C_RESET)
    if breadcrumb:
        print(C_DIM + "  > " + breadcrumb + C_RESET)
        hr(w)


def _get_git_branch():
    try:
        proc = subprocess.Popen(["git", "rev-parse", "--abbrev-ref", "HEAD"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, _ = proc.communicate()
        if proc.returncode == 0:
            return (out.decode("utf-8") if not PY2 and isinstance(out, bytes) else out).strip()
    except Exception:
        pass
    return ""


def print_status(cfg):
    provider = cfg.get("provider", "-")
    model = cfg.get("model", "-") or "-"
    key = cfg.get("api_key", "")
    key_disp = (key[:4] + "..." + key[-4:]) if len(key) > 8 else ("set" if key else C_RED + "not set" + C_RESET)
    cwd = os.path.basename(os.getcwd()) or os.getcwd()
    branch = _get_git_branch()
    git_disp = (C_DIM + "  |  git " + C_RESET + C_CYAN + branch + C_RESET) if branch else ""
    w = safe_width()
    print(C_DIM + " provider " + C_RESET + C_GREEN + provider + C_RESET +
          C_DIM + "  |  model " + C_RESET + C_GREEN + model + C_RESET +
          C_DIM + "  |  key " + C_RESET + C_GREEN + key_disp + C_RESET +
          C_DIM + "  |  cwd " + C_RESET + C_YELLOW + cwd + C_RESET + git_disp)
    hr(w)


def print_tool(name, args):
    print(C_BLUE + C_BOLD + " [tool]   " + C_RESET + C_BLUE + name + C_RESET + " " +
          C_DIM + json.dumps(args)[:200] + C_RESET)


def print_result(result):
    ok = result.get("ok", True) if isinstance(result, dict) else True
    tag = (C_GREEN + " [ok]     " + C_RESET) if ok else (C_RED + " [failed] " + C_RESET)
    body = json.dumps(result)
    if len(body) > 800:
        body = body[:800] + "...(truncated)"
    print(tag + body)


def print_agent(msg):
    print(C_MAGENTA + C_BOLD + " [skiff]  " + C_RESET + msg)


def print_error(msg):
    print(C_RED + C_BOLD + " [error]  " + C_RESET + C_RED + msg + C_RESET)


def print_working(label="thinking"):
    print(C_DIM + " ...%s..." % label + C_RESET)


def prompt_input(label):
    try:
        return input(C_YELLOW + label + C_RESET)
    except (EOFError, KeyboardInterrupt):
        print("")
        return None


CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".skiff")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
HISTORY_FILE = os.path.join(CONFIG_DIR, "history.json")

DEFAULT_CONFIG = {
    "provider": "openai",
    "api_key": "",
    "base_url": "",
    "model": "",
    "max_tokens": 4096,
    "system_prompt_extra": "",
    "total_tokens_used": 0,
    "total_cost_usd": 0.0
}

PROVIDER_DEFAULTS = {
    "openai": {
        "base_url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4o-mini",
        "style": "openai"
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1/messages",
        "model": "claude-sonnet-4-6",
        "style": "anthropic"
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "model": "openai/gpt-4o-mini",
        "style": "openai"
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "model": "llama-3.3-70b-versatile",
        "style": "openai"
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1/chat/completions",
        "model": "llama3.1",
        "style": "openai"
    },
    "local_gguf": {
        "base_url": "",
        "model": "",
        "style": "ollama_cli"
    },
    "custom": {
        "base_url": "",
        "model": "",
        "style": "openai"
    }
}

# Rough per-1K-token USD costs for the local cost monitor. Unknown models = 0.
COST_TABLE = {
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4o": (0.0025, 0.01),
    "claude-sonnet-4-6": (0.003, 0.015),
    "llama-3.3-70b-versatile": (0.0, 0.0),
}

SYSTEM_PROMPT_BASE = (
    "You are Skiff, an autonomous AI coding agent running in a local CLI. "
    "You have tools to read/write/list/delete files, inspect file metadata, search files, "
    "execute shell commands, inspect code structure, map repositories, run git diffs, run tests, "
    "and call MCP tools if configured. Use tools by responding with a single JSON "
    "object and nothing else, in this exact format:\n"
    '{"tool": "<tool_name>", "args": {...}}\n'
    "Available tools:\n"
    "  read_file(path)\n"
    "  write_file(path, content)\n"
    "  append_file(path, content)\n"
    "  patch_file(path, old_str, new_str)  - exact-match replace, for surgical edits\n"
    "  list_dir(path)\n"
    "  file_info(path)  - detailed metadata: size, permissions, modified time\n"
    "  search_files(path, pattern)  - regex code search across files in a path\n"
    "  delete_path(path)\n"
    "  make_dir(path)\n"
    "  run_command(cmd)\n"
    "  index_code(path)  - parse a Python file's AST: functions, classes, imports\n"
    "  map_repo(path)  - directory tree + per-file code index, for repo-wide context\n"
    "  git_diff()  - current working tree diff\n"
    "  git_status()\n"
    "  run_tests(cmd)  - run a test command, capture output for self-healing loops\n"
    "  mcp_call(server, method, params)  - call a configured MCP server\n"
    "  plan(steps)  - record a multi-step plan (list of strings) before executing\n"
    "  final_answer(message)\n"
    "For non-trivial tasks, call plan first with your step list, then execute "
    "steps one tool call at a time. If run_tests or run_command reports a "
    "failure, read the error, patch the relevant file, and re-run until it "
    "passes or you've tried 3 times - this is your self-healing loop. "
    "When done, or you just want to talk, respond with final_answer. Only ever "
    "output ONE JSON object per turn, no prose, no markdown fences."
)


def ensure_config_dir():
    if not os.path.isdir(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)


def load_config():
    ensure_config_dir()
    if os.path.isfile(CONFIG_FILE):
        f = open(CONFIG_FILE, "r")
        try:
            data = json.load(f)
        finally:
            f.close()
        cfg = dict(DEFAULT_CONFIG)
        cfg.update(data)
        return cfg
    return dict(DEFAULT_CONFIG)


def save_config(cfg):
    ensure_config_dir()
    f = open(CONFIG_FILE, "w")
    try:
        json.dump(cfg, f, indent=2)
    finally:
        f.close()


def load_history():
    if os.path.isfile(HISTORY_FILE):
        f = open(HISTORY_FILE, "r")
        try:
            return json.load(f)
        finally:
            f.close()
    return []


def save_history(hist):
    ensure_config_dir()
    f = open(HISTORY_FILE, "w")
    try:
        json.dump(hist, f, indent=2)
    finally:
        f.close()


# ---------------------------------------------------------------------------
# Setup / BYOK wizard
# ---------------------------------------------------------------------------

def cmd_setup(quick=False):
    cfg = load_config()
    print("Welcome to Skiff! Let's connect your AI key (BYOK).")
    print("1) OpenAI  2) Anthropic  3) OpenRouter  4) Groq  5) Ollama (local)  6) Local GGUF (offline)  7) Custom")
    choice = input("Pick a number [1]: ").strip()
    provider_map = {"1": "openai", "2": "anthropic", "3": "openrouter", "4": "groq",
                     "5": "ollama", "6": "local_gguf", "7": "custom"}
    provider = provider_map.get(choice, "openai")
    defaults = PROVIDER_DEFAULTS.get(provider, PROVIDER_DEFAULTS["custom"])

    api_key = ""
    if provider not in ("ollama", "local_gguf"):
        api_key = input("Paste your API key: ").strip()
        while not api_key:
            api_key = input("An API key is required. Paste your API key: ").strip()
    else:
        print("No API key needed - this runs fully offline/local.")

    base_url = defaults["base_url"]
    model = defaults["model"]
    if provider == "custom":
        base_url = input("Base URL: ").strip()
        model = input("Model name: ").strip()
    elif provider == "local_gguf":
        model = input("Local model name (as known to 'ollama') [%s]: " % (model or "llama3.1")).strip() or "llama3.1"
    else:
        custom_model = input("Model [%s] (press Enter to keep default): " % model).strip()
        if custom_model:
            model = custom_model

    cfg["provider"] = provider
    cfg["api_key"] = api_key
    cfg["base_url"] = base_url
    cfg["model"] = model
    save_config(cfg)
    print("All set! You're ready to use Skiff.\n")


def ensure_ready(cfg):
    if not cfg.get("api_key"):
        cmd_setup()
        return load_config()
    return cfg


# ---------------------------------------------------------------------------
# HTTP call (stdlib only, works on py2.7+ and py3)
# ---------------------------------------------------------------------------

RETRYABLE_HTTP_CODES = (429, 500, 502, 503, 504)


def http_post_json(url, headers, payload, timeout=120, max_retries=3):
    data = json.dumps(payload)
    if not PY2:
        data = data.encode("utf-8")
    ctx = None
    try:
        ctx = _ssl.create_default_context()
    except Exception:
        ctx = None

    last_err = None
    for attempt in range(max_retries):
        req = _urlreq.Request(url, data=data)
        for k, v in headers.items():
            req.add_header(k, v)
        try:
            if ctx is not None:
                resp = _urlreq.urlopen(req, timeout=timeout, context=ctx)
            else:
                resp = _urlreq.urlopen(req, timeout=timeout)
            body = resp.read()
            if not PY2:
                body = body.decode("utf-8")
            return json.loads(body)
        except Exception as e:
            code = getattr(e, "code", None)
            err_body = None
            try:
                err_body = e.read()
                if not PY2 and err_body is not None:
                    err_body = err_body.decode("utf-8")
            except Exception:
                pass
            last_err = "HTTP error calling provider: %s%s" % (
                str(e), ("\nBody: %s" % err_body) if err_body else "")
            if code in RETRYABLE_HTTP_CODES and attempt < max_retries - 1:
                time.sleep(min(2 ** attempt, 8))
                continue
            raise RuntimeError(last_err)
    raise RuntimeError(last_err or "Unknown HTTP failure")


def call_model(cfg, messages):
    provider = cfg.get("provider", "openai")
    style = PROVIDER_DEFAULTS.get(provider, PROVIDER_DEFAULTS["custom"])["style"]
    api_key = os.environ.get("SKIFF_API_KEY") or cfg.get("api_key", "")
    base_url = cfg.get("base_url") or PROVIDER_DEFAULTS.get(provider, {}).get("base_url", "")
    model = cfg.get("model") or PROVIDER_DEFAULTS.get(provider, {}).get("model", "")
    max_tokens = cfg.get("max_tokens", 4096)

    if style == "ollama_cli":
        # Offline/air-gapped local GGUF execution via the `ollama` binary.
        # No network call - shells out to a locally running model.
        prompt = ""
        for m in messages:
            prompt += "[%s]\n%s\n" % (m["role"], m["content"])
        try:
            proc = subprocess.Popen(
                ["ollama", "run", model or "llama3.1"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            )
            out, _ = proc.communicate(input=(prompt if PY2 else prompt.encode("utf-8")))
            if not PY2 and isinstance(out, bytes):
                out = out.decode("utf-8", errors="replace")
            return out, 0, 0
        except Exception as e:
            raise RuntimeError("Local model execution failed (is 'ollama' installed and on PATH?): %s" % str(e))

    if not api_key and style != "ollama_cli":
        if provider != "ollama":
            raise RuntimeError("No API key configured. Run: skiff setup")
    if not base_url:
        raise RuntimeError("No base_url configured. Run: skiff setup")

    if style == "anthropic":
        sys_msg = ""
        conv = []
        for m in messages:
            if m["role"] == "system":
                sys_msg += m["content"] + "\n"
            else:
                conv.append({"role": m["role"], "content": m["content"]})
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "system": sys_msg,
            "messages": conv
        }
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        result = http_post_json(base_url, headers, payload)
        blocks = result.get("content", [])
        out = ""
        for b in blocks:
            if b.get("type") == "text":
                out += b.get("text", "")
        usage = result.get("usage", {})
        in_tok = usage.get("input_tokens", 0)
        out_tok = usage.get("output_tokens", 0)
        return out, in_tok, out_tok
    else:
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages
        }
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = "Bearer " + api_key
        result = http_post_json(base_url, headers, payload)
        choices = result.get("choices", [])
        if not choices:
            raise RuntimeError("No choices in response: %s" % json.dumps(result))
        usage = result.get("usage", {})
        in_tok = usage.get("prompt_tokens", 0)
        out_tok = usage.get("completion_tokens", 0)
        return choices[0]["message"]["content"], in_tok, out_tok


def track_usage(cfg, model, in_tok, out_tok):
    cfg["total_tokens_used"] = cfg.get("total_tokens_used", 0) + in_tok + out_tok
    rates = COST_TABLE.get(model, (0.0, 0.0))
    cost = (in_tok / 1000.0) * rates[0] + (out_tok / 1000.0) * rates[1]
    cfg["total_cost_usd"] = round(cfg.get("total_cost_usd", 0.0) + cost, 6)
    save_config(cfg)


# ---------------------------------------------------------------------------
# Tools - file management + command execution
# ---------------------------------------------------------------------------

def _safe_path(p):
    return os.path.abspath(os.path.expanduser(p))


def tool_read_file(args):
    path = _safe_path(args.get("path", ""))
    if not os.path.isfile(path):
        return {"ok": False, "error": "File not found: %s" % path}
    f = open(path, "r")
    try:
        content = f.read()
    finally:
        f.close()
    return {"ok": True, "content": content}


SKIFF_VERSION = "1.0.0"


def _backup_before_overwrite(path):
    """Undo safety net: keep the previous version of any file before Skiff
    overwrites it, so file-management stays reversible."""
    if not os.path.isfile(path):
        return
    ensure_config_dir()
    backup_dir = os.path.join(CONFIG_DIR, "backups")
    if not os.path.isdir(backup_dir):
        os.makedirs(backup_dir)
    stamp = str(int(time.time() * 1000))
    path_bytes = path.encode("utf-8") if isinstance(path, text_type) else str(path).encode("utf-8")
    name = hashlib.sha1(path_bytes).hexdigest()[:10]
    dest = os.path.join(backup_dir, "%s_%s_%s" % (name, stamp, os.path.basename(path)))
    try:
        shutil.copy2(path, dest)
    except Exception:
        pass


def tool_write_file(args):
    path = _safe_path(args.get("path", ""))
    content = args.get("content", "")
    _backup_before_overwrite(path)
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    f = open(path, "w")
    try:
        f.write(content)
    finally:
        f.close()
    return {"ok": True, "message": "Wrote %d bytes to %s" % (len(content), path)}


def tool_append_file(args):
    path = _safe_path(args.get("path", ""))
    content = args.get("content", "")
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    f = open(path, "a")
    try:
        f.write(content)
    finally:
        f.close()
    return {"ok": True, "message": "Appended %d bytes to %s" % (len(content), path)}


def tool_list_dir(args):
    path = _safe_path(args.get("path", "."))
    if not os.path.isdir(path):
        return {"ok": False, "error": "Not a directory: %s" % path}
    entries = []
    for name in sorted(os.listdir(path)):
        full = os.path.join(path, name)
        entries.append({
            "name": name,
            "is_dir": os.path.isdir(full),
            "size": os.path.getsize(full) if os.path.isfile(full) else None
        })
    return {"ok": True, "entries": entries}


def tool_delete_path(args):
    path = _safe_path(args.get("path", ""))
    if os.path.isfile(path):
        _backup_before_overwrite(path)
        os.remove(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)
    else:
        return {"ok": False, "error": "Path not found: %s" % path}
    return {"ok": True, "message": "Deleted %s" % path}


def tool_file_info(args):
    path = _safe_path(args.get("path", ""))
    if not os.path.exists(path):
        return {"ok": False, "error": "Path not found: %s" % path}
    st = os.stat(path)
    return {
        "ok": True,
        "path": path,
        "is_dir": os.path.isdir(path),
        "size_bytes": st.st_size,
        "mode": oct(st.st_mode),
        "mtime": time.ctime(st.st_mtime)
    }


def tool_search_files(args):
    root = _safe_path(args.get("path", "."))
    pattern = args.get("pattern", "")
    if not pattern:
        return {"ok": False, "error": "Empty pattern"}
    try:
        regex = re.compile(pattern)
    except Exception as e:
        return {"ok": False, "error": "Invalid regex pattern: %s" % str(e)}

    patterns = _load_skiffignore(root)
    matches = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        rel = os.path.relpath(dirpath, root)
        for fn in filenames:
            relfull = os.path.normpath(os.path.join(rel, fn))
            if _is_ignored(relfull, patterns):
                continue
            full = os.path.join(dirpath, fn)
            try:
                f = open(full, "r")
                try:
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            matches.append({
                                "file": relfull,
                                "line": line_num,
                                "text": line.strip()[:200]
                            })
                            if len(matches) >= 500:
                                break
                finally:
                    f.close()
            except Exception:
                pass
            if len(matches) >= 500:
                break
        if len(matches) >= 500:
            break
    return {"ok": True, "match_count": len(matches), "matches": matches}


def tool_make_dir(args):
    path = _safe_path(args.get("path", ""))
    if not os.path.isdir(path):
        os.makedirs(path)
    return {"ok": True, "message": "Created %s" % path}


def tool_run_command(args):
    cmd = args.get("cmd", "")
    if not cmd:
        return {"ok": False, "error": "Empty command"}
    try:
        proc = subprocess.Popen(
            cmd, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        out, _ = proc.communicate()
        if not PY2 and isinstance(out, bytes):
            out = out.decode("utf-8", errors="replace")
        return {"ok": True, "output": out, "returncode": proc.returncode}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_patch_file(args):
    path = _safe_path(args.get("path", ""))
    old_str = args.get("old_str", "")
    new_str = args.get("new_str", "")
    if not os.path.isfile(path):
        return {"ok": False, "error": "File not found: %s" % path}
    f = open(path, "r")
    try:
        content = f.read()
    finally:
        f.close()
    count = content.count(old_str)
    if count != 1:
        return {"ok": False, "error": "old_str matched %d times, need exactly 1" % count}
    _backup_before_overwrite(path)
    content = content.replace(old_str, new_str, 1)
    f = open(path, "w")
    try:
        f.write(content)
    finally:
        f.close()
    return {"ok": True, "message": "Patched %s" % path}


def _index_python_file(path):
    try:
        f = open(path, "r")
        try:
            src = f.read()
        finally:
            f.close()
        tree = ast.parse(src)
    except Exception as e:
        return {"error": str(e)}
    funcs, classes, imports = [], [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            funcs.append(node.name)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                imports.append(a.name)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    return {"functions": funcs, "classes": classes, "imports": imports}


def tool_index_code(args):
    path = _safe_path(args.get("path", ""))
    if not os.path.isfile(path):
        return {"ok": False, "error": "File not found: %s" % path}
    if not path.endswith(".py"):
        return {"ok": False, "error": "AST indexing only supports .py files"}
    result = _index_python_file(path)
    return {"ok": "error" not in result, "index": result}


IGNORE_DIRS = set([".git", "node_modules", "__pycache__", ".skiff", "venv", ".venv"])


def _load_skiffignore(root):
    """Simple .skiffignore support: one glob pattern per line, matched against
    each file's path relative to root. No external deps - fnmatch is stdlib."""
    import fnmatch
    path = os.path.join(root, ".skiffignore")
    patterns = []
    if os.path.isfile(path):
        f = open(path, "r")
        try:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
        finally:
            f.close()
    return patterns


def _is_ignored(relpath, patterns):
    import fnmatch
    for pat in patterns:
        if fnmatch.fnmatch(relpath, pat) or fnmatch.fnmatch(os.path.basename(relpath), pat):
            return True
    return False


def tool_map_repo(args):
    root = _safe_path(args.get("path", "."))
    if not os.path.isdir(root):
        return {"ok": False, "error": "Not a directory: %s" % root}
    patterns = _load_skiffignore(root)
    tree = []
    py_index = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        rel = os.path.relpath(dirpath, root)
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            relfull = os.path.normpath(os.path.join(rel, fn))
            if _is_ignored(relfull, patterns):
                continue
            tree.append(relfull)
            if fn.endswith(".py"):
                py_index[relfull] = _index_python_file(full)
        if len(tree) > 2000:
            break
    return {"ok": True, "file_count": len(tree), "files": tree[:2000], "python_index": py_index}


def tool_git_diff(args):
    return tool_run_command({"cmd": "git diff"})


def tool_git_status(args):
    return tool_run_command({"cmd": "git status --porcelain"})


def tool_run_tests(args):
    cmd = args.get("cmd", "")
    if not cmd:
        return {"ok": False, "error": "No test command given"}
    return tool_run_command({"cmd": cmd})


def load_mcp_servers():
    ensure_config_dir()
    path = os.path.join(CONFIG_DIR, "mcp.json")
    if os.path.isfile(path):
        f = open(path, "r")
        try:
            return json.load(f)
        finally:
            f.close()
    return {}


def tool_mcp_call(args):
    servers = load_mcp_servers()
    name = args.get("server", "")
    method = args.get("method", "")
    params = args.get("params", {})
    if name not in servers:
        return {"ok": False, "error": "Unknown MCP server '%s'. Configure it in %s/mcp.json" % (name, CONFIG_DIR)}
    url = servers[name].get("url", "")
    if not url:
        return {"ok": False, "error": "Server '%s' has no url configured" % name}
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    try:
        result = http_post_json(url, {"Content-Type": "application/json"}, payload)
        return {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tool_plan(args):
    steps = args.get("steps", [])
    ensure_config_dir()
    path = os.path.join(CONFIG_DIR, "last_plan.json")
    f = open(path, "w")
    try:
        json.dump({"steps": steps, "ts": time.time()}, f, indent=2)
    finally:
        f.close()
    return {"ok": True, "message": "Plan recorded (%d steps)" % len(steps), "steps": steps}


TOOLS = {
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "append_file": tool_append_file,
    "patch_file": tool_patch_file,
    "list_dir": tool_list_dir,
    "file_info": tool_file_info,
    "search_files": tool_search_files,
    "delete_path": tool_delete_path,
    "make_dir": tool_make_dir,
    "run_command": tool_run_command,
    "index_code": tool_index_code,
    "map_repo": tool_map_repo,
    "git_diff": tool_git_diff,
    "git_status": tool_git_status,
    "run_tests": tool_run_tests,
    "mcp_call": tool_mcp_call,
    "plan": tool_plan
}

# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

def extract_json(text):
    text = text.strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    idx = 0
    dec = json.JSONDecoder()
    candidate = None
    while idx < len(text):
        start = text.find("{", idx)
        if start == -1:
            break
        try:
            obj, end = dec.raw_decode(text[start:])
            if isinstance(obj, dict):
                if "tool" in obj:
                    return obj
                if candidate is None:
                    candidate = obj
            idx = start + (end if end > 0 else 1)
        except Exception:
            idx = start + 1

    return candidate


def load_ambient_context(root="."):
    """Auto-load project context files used by other AI coding tools, so Skiff
    respects them too: CLAUDE.md (Claude Code), .cursorrules (Cursor),
    .github/copilot-instructions.md, opencode.json (OpenCode), and
    .vscode/settings.json's relevant custom-instruction fields."""
    root = _safe_path(root)
    chunks = []
    candidates = [
        ("CLAUDE.md", "Claude Code project instructions"),
        (".cursorrules", "Cursor rules"),
        (os.path.join(".github", "copilot-instructions.md"), "Copilot instructions"),
        ("opencode.json", "OpenCode config"),
        ("AGENTS.md", "Agent instructions"),
    ]
    for rel, label in candidates:
        full = os.path.join(root, rel)
        if os.path.isfile(full):
            try:
                f = open(full, "r")
                try:
                    content = f.read()
                finally:
                    f.close()
                chunks.append("### %s (%s)\n%s" % (label, rel, content[:4000]))
            except Exception:
                pass
    vscode_settings = os.path.join(root, ".vscode", "settings.json")
    if os.path.isfile(vscode_settings):
        try:
            f = open(vscode_settings, "r")
            try:
                data = json.load(f)
            finally:
                f.close()
            for key in list(data.keys()):
                if "instructions" in key.lower() or "prompt" in key.lower():
                    chunks.append("### VS Code setting %s\n%s" % (key, json.dumps(data[key])[:2000]))
        except Exception:
            pass
    return "\n\n".join(chunks)


def load_plugins():
    """Load user-added Python tool plugins from ~/.skiff/plugins/*.py so
    features can be dropped in from Claude Code, VS Code, Cursor, OpenCode
    workflows without editing skiff.py. Each plugin module must define
    TOOL_NAME (str), TOOL_DESC (str), and run(args) -> dict."""
    ensure_config_dir()
    plugin_dir = os.path.join(CONFIG_DIR, "plugins")
    if not os.path.isdir(plugin_dir):
        os.makedirs(plugin_dir)
        return {}, ""
    loaded = {}
    descs = []
    sys.path.insert(0, plugin_dir)
    for fn in sorted(os.listdir(plugin_dir)):
        if not fn.endswith(".py"):
            continue
        modname = fn[:-3]
        try:
            mod = __import__(modname)
            name = getattr(mod, "TOOL_NAME", modname)
            desc = getattr(mod, "TOOL_DESC", "")
            runner = getattr(mod, "run", None)
            if runner:
                loaded[name] = runner
                descs.append("  %s(args)  - %s [plugin: %s]" % (name, desc, fn))
        except Exception as e:
            print("[warn] failed to load plugin %s: %s" % (fn, str(e)))
    return loaded, "\n".join(descs)


PLUGIN_TOOLS, PLUGIN_TOOL_DOCS = load_plugins()
TOOLS_EXTRA_DOC = PLUGIN_TOOL_DOCS
TOOLS.update(PLUGIN_TOOLS)


def new_session_id():
    return hashlib.sha1(text_type(time.time()).encode("utf-8") if not PY2 else str(time.time())).hexdigest()[:10]


def append_session_history(session_id, messages):
    hist = load_history()
    hist.append({"id": session_id, "ts": time.time(), "messages": messages})
    hist = hist[-50:]  # keep last 50 sessions, lightweight
    save_history(hist)


def run_agent(cfg, task, auto_confirm=True, max_turns=25):
    system_prompt = SYSTEM_PROMPT_BASE
    if TOOLS_EXTRA_DOC:
        system_prompt += "\n\nAdditional plugin tools available:\n" + TOOLS_EXTRA_DOC
    ambient = load_ambient_context(".")
    if ambient:
        system_prompt += "\n\nProject context found on disk (from CLAUDE.md / .cursorrules / copilot / opencode / AGENTS.md):\n" + ambient
    extra = cfg.get("system_prompt_extra", "")
    if extra:
        system_prompt += "\n\nUser custom instructions:\n" + extra

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task}
    ]
    session_id = new_session_id()
    for turn in range(max_turns):
        print_working("thinking (turn %d/%d)" % (turn + 1, max_turns))
        try:
            reply, in_tok, out_tok = call_model(cfg, messages)
            track_usage(cfg, cfg.get("model", ""), in_tok, out_tok)
        except Exception as e:
            print_error(str(e))
            append_session_history(session_id, messages)
            return
        parsed = extract_json(reply)
        if parsed is None:
            print_agent(reply)
            messages.append({"role": "assistant", "content": reply})
            append_session_history(session_id, messages)
            return
        tool_name = parsed.get("tool")
        args = parsed.get("args", {})
        if tool_name == "final_answer":
            print_agent(args.get("message", ""))
            messages.append({"role": "assistant", "content": reply})
            append_session_history(session_id, messages)
            return
        if tool_name not in TOOLS:
            print_error("Unknown tool: %s" % tool_name)
            messages.append({"role": "assistant", "content": reply})
            messages.append({"role": "user", "content": json.dumps({"error": "unknown tool"})})
            continue

        print_tool(tool_name, args)
        result = TOOLS[tool_name](args)
        print_result(result)
        messages.append({"role": "assistant", "content": reply})
        messages.append({"role": "user", "content": json.dumps(result)})
    print_agent("Max turns reached (%d). Stopping." % max_turns)
    append_session_history(session_id, messages)


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

def print_usage():
    print("Skiff v%s - BYOK AI Coding Agent CLI" % SKIFF_VERSION)
    print("Usage:")
    print("  skiff                      Launch the TUI menu (default)")
    print("  skiff setup                Configure provider/API key/model")
    print("  skiff chat                 Interactive chat/agent session")
    print("  skiff run \"<task>\"         Run a single agent task")
    print("  skiff config               Show current config (key masked)")
    print("  skiff config export <file> Export config (API key redacted) to a JSON file")
    print("  skiff config import <file> Import config from a JSON file")
    print("  skiff usage                Show token usage & estimated cost")
    print("  skiff history              List recent sessions")
    print("  skiff --version            Show version")
    print("  skiff <anything else>      Also runs it as a task, no setup needed first time")
    print("")
    print("Env override: SKIFF_API_KEY takes precedence over the saved key.")


def cmd_config_export(dest):
    cfg = load_config()
    shown = dict(cfg)
    if shown.get("api_key"):
        shown["api_key"] = ""  # never export secrets
    f = open(dest, "w")
    try:
        json.dump(shown, f, indent=2)
    finally:
        f.close()
    print("Exported (API key redacted) to %s" % dest)


def cmd_config_import(src):
    if not os.path.isfile(src):
        print_error("File not found: %s" % src)
        return
    f = open(src, "r")
    try:
        data = json.load(f)
    finally:
        f.close()
    cfg = load_config()
    for k in ("provider", "base_url", "model", "max_tokens", "system_prompt_extra"):
        if k in data:
            cfg[k] = data[k]
    if data.get("api_key"):
        cfg["api_key"] = data["api_key"]
    save_config(cfg)
    print("Imported config from %s" % src)


def cmd_usage():
    cfg = load_config()
    print("Total tokens used: %s" % cfg.get("total_tokens_used", 0))
    print("Estimated cost:    $%.6f" % cfg.get("total_cost_usd", 0.0))


def cmd_history():
    hist = load_history()
    if not hist:
        print("No sessions recorded yet.")
        return
    for i, s in enumerate(hist[-15:]):
        first_user = ""
        for m in s.get("messages", []):
            if m["role"] == "user" and not m["content"].startswith("{"):
                first_user = m["content"]
                break
        print("%2d) %s  %s" % (i + 1, s.get("id", "?"), first_user[:60]))


def cmd_config():
    cfg = load_config()
    shown = dict(cfg)
    if shown.get("api_key"):
        k = shown["api_key"]
        shown["api_key"] = k[:4] + "..." + k[-4:] if len(k) > 8 else "****"
    print(json.dumps(shown, indent=2))


def cmd_chat(cfg):
    cfg = ensure_ready(cfg)
    print("Skiff is ready. Just type what you want done. Type 'exit' to quit.")
    while True:
        try:
            task = input("you> ")
        except (EOFError, KeyboardInterrupt):
            print("")
            break
        if task.strip().lower() in ("exit", "quit"):
            break
        if not task.strip():
            continue
        run_agent(cfg, task)


# ---------------------------------------------------------------------------
# TUI (plain-text, no curses - works on XP cmd.exe through Win11 Terminal,
# and on Linux/macOS shells)
# ---------------------------------------------------------------------------

def footer_pause():
    hr()
    prompt_input(" Press Enter to return to menu... ")


def tui_menu():
    print_banner()
    cfg = load_config()
    print_status(cfg)
    items = [
        ("1", "Chat with Skiff (agent session)"),
        ("2", "Run a single task"),
        ("3", "Setup / change API key & model"),
        ("4", "Show config"),
        ("5", "Help"),
        ("6", "Token usage & cost monitor"),
        ("7", "Custom system instructions"),
        ("8", "Session history / replay"),
        ("9", "MCP servers"),
        ("P", "Plugins (Claude Code / Cursor / VS Code / OpenCode extras)"),
        ("0", "Exit"),
    ]
    for key, label in items:
        print(" " + C_BOLD + C_CYAN + ("[%s]" % key).ljust(4) + C_RESET + label)
    hr()
    return set(k for k, _ in items)


def tui_usage(cfg):
    clear_screen()
    print_banner("Token usage & cost monitor")
    print(" Total tokens used: " + C_GREEN + str(cfg.get("total_tokens_used", 0)) + C_RESET)
    print(" Estimated cost:    " + C_GREEN + ("$%.6f" % cfg.get("total_cost_usd", 0.0)) + C_RESET)
    print(C_DIM + " (cost estimates only cover known models in COST_TABLE)" + C_RESET)
    footer_pause()


def tui_custom_prompt(cfg):
    clear_screen()
    print_banner("Custom system instructions")
    print(" Current:")
    print(" " + (cfg.get("system_prompt_extra", "") or C_DIM + "(none)" + C_RESET))
    hr()
    new_text = prompt_input(" Enter new instructions (blank = keep current):\n > ")
    if new_text and new_text.strip():
        cfg["system_prompt_extra"] = new_text.strip()
        save_config(cfg)
        print(C_GREEN + " Saved." + C_RESET)
    footer_pause()


def tui_history(cfg):
    clear_screen()
    print_banner("Session history / replay")
    hist = load_history()
    if not hist:
        print(C_DIM + " No sessions recorded yet." + C_RESET)
    else:
        for i, s in enumerate(hist[-15:]):
            first_user = ""
            for m in s.get("messages", []):
                if m["role"] == "user" and not m["content"].startswith("{"):
                    first_user = m["content"]
                    break
            print(" %2d) %s  %s" % (i + 1, s.get("id", "?"), first_user[:60]))
        hr()
        pick = prompt_input(" Enter number to replay full transcript (blank = back): ")
        pick = (pick or "").strip()
        if pick.isdigit():
            idx = int(pick) - 1
            recent = hist[-15:]
            if 0 <= idx < len(recent):
                clear_screen()
                print_banner("Session history / replay / transcript")
                for m in recent[idx]["messages"]:
                    print(C_BOLD + "-- %s --" % m["role"] + C_RESET)
                    print(m["content"][:1000])
                    print("")
            else:
                print_error("No such session number.")
    footer_pause()


def tui_plugins(cfg):
    clear_screen()
    print_banner("Plugins")
    plugin_dir = os.path.join(CONFIG_DIR, "plugins")
    print(" Plugin folder: " + C_GREEN + plugin_dir + C_RESET)
    print(" Drop a .py file here defining TOOL_NAME, TOOL_DESC, run(args)->dict")
    print(" to add a tool the agent can call - a lightweight way to port over")
    print(" features/snippets from Claude Code, Cursor, VS Code, or OpenCode.")
    print(" Also auto-read as ambient context each run: CLAUDE.md, .cursorrules,")
    print(" .github/copilot-instructions.md, opencode.json, AGENTS.md")
    hr()
    if PLUGIN_TOOLS:
        print(" Loaded plugin tools:")
        print(TOOLS_EXTRA_DOC)
    else:
        print(C_DIM + " No plugins loaded yet." + C_RESET)
    footer_pause()


def tui_mcp(cfg):
    clear_screen()
    print_banner("MCP servers")
    servers = load_mcp_servers()
    print(" Configured MCP servers:")
    if not servers:
        print(C_DIM + "   (none)" + C_RESET)
    for name, info in servers.items():
        print("   %s -> %s" % (name, info.get("url", "")))
    hr()
    name = prompt_input(" Add server (name, blank = back): ")
    name = (name or "").strip()
    if name:
        url = prompt_input(" Server URL (JSON-RPC endpoint): ")
        url = (url or "").strip()
        if url:
            servers[name] = {"url": url}
            ensure_config_dir()
            path = os.path.join(CONFIG_DIR, "mcp.json")
            f = open(path, "w")
            try:
                json.dump(servers, f, indent=2)
            finally:
                f.close()
            print(C_GREEN + " Saved." + C_RESET)
    footer_pause()


def tui_chat_session(cfg):
    clear_screen()
    print_banner("Chat session")
    print_status(cfg)
    print(" Type your task in plain English.")
    print(C_DIM + " Slash commands: /clear, /history, /config, /help, /plan, /menu, /exit" + C_RESET + "\n")
    turn = 0
    while True:
        task = prompt_input(" you> ")
        if task is None:
            return "exit"
        low = task.strip().lower()
        if low in ("menu", "/menu"):
            return "menu"
        if low in ("exit", "quit", "/exit"):
            return "exit"
        if low == "/clear":
            clear_screen()
            print_banner("Chat session")
            print_status(cfg)
            continue
        if low == "/history":
            cmd_history()
            continue
        if low == "/config":
            cmd_config()
            continue
        if low == "/help":
            print(C_CYAN + "Available slash commands:" + C_RESET)
            print("  /clear   - Clear terminal screen")
            print("  /history - View session history")
            print("  /config  - View active configuration")
            print("  /plan    - View last recorded plan")
            print("  /menu    - Return to main TUI menu")
            print("  /exit    - Exit Skiff")
            continue
        if low == "/plan":
            path = os.path.join(CONFIG_DIR, "last_plan.json")
            if os.path.isfile(path):
                f = open(path, "r")
                try:
                    data = json.load(f)
                    print(C_GREEN + "Last recorded plan:" + C_RESET)
                    for idx, step in enumerate(data.get("steps", [])):
                        print("  %d. %s" % (idx + 1, step))
                finally:
                    f.close()
            else:
                print(C_DIM + "No plan recorded yet." + C_RESET)
            continue

        if not task.strip():
            continue
        turn += 1
        hr()
        run_agent(cfg, task)
        hr()


def tui_run_once(cfg):
    clear_screen()
    print_banner("Run a single task")
    print_status(cfg)
    task = prompt_input(" What do you want Skiff to do?\n > ")
    if task and task.strip():
        hr()
        run_agent(cfg, task)
    footer_pause()


def tui_help():
    clear_screen()
    print_banner("Help")
    print(" Skiff reads your request, decides which tool to use (read/write/list/")
    print(" delete files, make folders, run shell commands, git, tests, MCP),")
    print(" does it, and reports back - looping until the task is done.")
    print(" No setup steps to remember: first time you chat or run a task,")
    print(" it asks for your API key once (BYOK) and remembers it.")
    print("")
    print(" Menu shortcuts: numbers 0-9 plus P for plugins.")
    print(" Ctrl+C at any prompt safely returns you up a level.")
    footer_pause()


def run_tui():
    while True:
        valid_keys = tui_menu()
        choice = prompt_input(" select> ")
        if choice is None:
            return
        choice = choice.strip()
        if not choice:
            continue
        valid_keys_upper = set(k.upper() for k in valid_keys)
        if choice.upper() not in valid_keys_upper:
            print_error("Invalid choice '%s' - pick one of: %s" % (choice, ", ".join(sorted(valid_keys))))
            prompt_input(" Press Enter to continue... ")
            continue
        cfg = load_config()
        if choice == "1":
            cfg = ensure_ready(cfg)
            result = tui_chat_session(cfg)
            if result == "exit":
                return
        elif choice == "2":
            cfg = ensure_ready(cfg)
            tui_run_once(cfg)
        elif choice == "3":
            clear_screen()
            print_banner("Setup")
            cmd_setup()
            footer_pause()
        elif choice == "4":
            clear_screen()
            print_banner("Config")
            cmd_config()
            footer_pause()
        elif choice == "5":
            tui_help()
        elif choice == "6":
            tui_usage(cfg)
        elif choice == "7":
            tui_custom_prompt(cfg)
        elif choice == "8":
            tui_history(cfg)
        elif choice == "9":
            tui_mcp(cfg)
        elif choice.lower() == "p":
            tui_plugins(cfg)
        elif choice == "0":
            return


def main():
    args = sys.argv[1:]
    if not args:
        run_tui()
        return
    cmd = args[0]
    cfg = load_config()

    if cmd in ("--version", "-v", "version"):
        print("Skiff v%s" % SKIFF_VERSION)
    elif cmd in ("tui", "menu"):
        run_tui()
    elif cmd == "setup":
        cmd_setup()
    elif cmd == "config":
        if len(args) >= 3 and args[1] == "export":
            cmd_config_export(args[2])
        elif len(args) >= 3 and args[1] == "import":
            cmd_config_import(args[2])
        else:
            cmd_config()
    elif cmd == "usage":
        cmd_usage()
    elif cmd == "history":
        cmd_history()
    elif cmd == "chat":
        cmd_chat(cfg)
    elif cmd == "run":
        if len(args) < 2:
            print("Usage: skiff run \"<task>\"")
            return
        cfg = ensure_ready(cfg)
        task = args[1]
        run_agent(cfg, task)
    else:
        # beginner-friendly: treat any unrecognized input as a task
        cfg = ensure_ready(cfg)
        run_agent(cfg, " ".join(args))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception:
        traceback.print_exc()
        sys.exit(1)
