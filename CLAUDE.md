# CLAUDE.md

Essential guidance for Claude Code working on antidote.

## Project Overview

**antidote** - Personal AI assistant built in Python (~3k lines, 63 files) by Mark Kashef. Telegram bot interface with LiteLLM multi-model routing, SQLite FTS5 memory, and Fernet encryption.

**Codebase**: 3-level structure: Level 0 wrapper (`~/webdev/github/antidote/`) → Level 1 git repo (`antidote/`) → Level 2 Python package (`antidote/antidote/`)

## Session Start

```bash
cd ~/webdev/github/antidote && source antidote/.venv/bin/activate && antidote
```

**Manual**: read `project-state.md` for current status.

## Project rules

| Rule | Details |
|------|---------|
| Python only | Do NOT suggest npm, node, or any JS tooling for this project |
| OpenRouter model IDs | Use dots not dashes: `claude-haiku-4.5` NOT `claude-haiku-4-5-20251001` |
| No new JS dependencies | Even though some config may mention JS — this is a Python project |
| API keys in config | Never commit API keys — they live in `~/.antidote/config.json` |

## Stack

- **Language**: Python 3.14
- **LLM Routing**: LiteLLM via OpenRouter
- **Interface**: python-telegram-bot
- **Memory**: SQLite with FTS5 full-text search
- **Encryption**: Fernet (cryptography library)
- **Default model**: `anthropic/claude-sonnet-4` via OpenRouter
- **Model routing**: Haiku (`anthropic/claude-haiku-4.5`) for simple, Sonnet for complex

## Project Structure

```
~/webdev/github/antidote/          # Level 0: wrapper repo
├── antidote/                      # Level 1: main git repo (fork of earlyaidopters/antidote)
│   ├── antidote/                  # Level 2: Python package
│   │   ├── agent/loop.py          # Main conversation loop + model routing
│   │   ├── providers/openrouter.py # OpenRouter API integration
│   │   └── channels/, tools/, memory/, security/
│   ├── workspace/                 # identity, knowledge, reference MD files
│   │   ├── in/                    # Auto-saved user inputs >500 chars
│   │   └── out/                   # Auto-saved structured responses >12 lines
│   └── .venv/                     # Python virtual environment
├── project-state.md               # Current project state
└── start.sh                       # Startup convenience script
```

## Essential Commands

```bash
# Run bot (venv must already be active — see Session Start)
antidote

# Run tests
cd ~/webdev/github/antidote/antidote && python -m pytest

# Config holds API keys: check a key exists with grep -c, never print the file

# Workspace access
ls ~/webdev/github/antidote/antidote/workspace/
```

## Key Configuration

- **Config file**: `~/.antidote/config.json`
- **Workspace symlink**: `~/.antidote/workspace` → `~/webdev/github/antidote/antidote/workspace/`
- **Telegram bot**: `@antidote_br_dev_bot`
- **Chat ID (BR)**: `7747400769`

## Git Remotes

- **origin**: `BR4096/antidote` (BR's fork)
- **upstream**: `earlyaidopters/antidote` (Mark Kashef's original)

## Model Routing

Routing logic lives in `_classify_query()` in `loop.py`:
- **Simple queries** → Haiku (`anthropic/claude-haiku-4.5`) — heuristic keyword + length classifier
- **Complex queries** → Sonnet (`anthropic/claude-sonnet-4`)
- **Upgrade rule**: If Haiku returns tool calls, remaining rounds auto-upgrade to Sonnet

## Workspace Files

Markdown files in `antidote/workspace/`. Key identity files:
- `SOUL.md` — writing voice
- `USER.md` — personality profile
- `AGENTS.md` — knowledge catalog + trigger conditions

## Decision Trees

### File Creation

```
New feature      → antidote/antidote/ (Python package)
Config change    → ~/.antidote/config.json
Workspace docs   → antidote/workspace/
Tests            → antidote/tests/ (does not exist yet; pytest)
```

### Error Debugging

```
OpenRouter 400   → Check model ID format (dots not dashes)
Tool call error  → Check tool_call format in openrouter.py
Memory issue     → Check SQLite FTS5 in memory module
Bot offline      → Check @antidote_br_dev_bot status + API key
```

## Pre-commit

```bash
# Syntax check before committing; commit rules come from the global git-commits rule
python -m py_compile antidote/antidote/*.py
```

## NEVER

- Any JS/Node tooling (this is a Python project); other stack bans come from the global Stack Rules
- Hardcoded API keys or credentials in any source file
