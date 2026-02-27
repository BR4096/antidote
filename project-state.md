# Antidote — Project State

**Last updated:** 2026-02-27
**Repo:** `/Users/billringle/webdev/github/antidote/`
**Fork:** `github.com/BR4096/antidote` (origin)
**Upstream:** `github.com/earlyaidopters/antidote` (upstream)

## What Is Antidote

Personal AI assistant built in Python (~3,000 lines). Runs on Mac, talks via Telegram, remembers everything via SQLite FTS5. Uses OpenRouter for 100+ LLM models. Built by Mark Kashef.

## Current Status: Running — Reference-Aware Bot

### Done
- [x] Repo cloned to `~/webdev/github/antidote/`
- [x] Python 3.14 detected and compatible
- [x] Virtual environment created at `antidote/.venv/`
- [x] All dependencies installed via `pip install -e .`
- [x] Setup wizard completed — config written to `~/.antidote/config.json`
- [x] Memory database seeded at `~/.antidote/memory.db`
- [x] Bot running and responding to Telegram messages
- [x] Tool calls (memory search) verified working
- [x] OpenRouter credits added and billing confirmed
- [x] Identity files customized for Bill (SOUL.md, USER.md, AGENTS.md)
- [x] Workspace consolidated — single source of truth in repo (see Workspace section)
- [x] SOUL.md enriched with writing voice guidance (from writeprint analysis)
- [x] USER.md enriched with personality profile and positioning language (from BR_OS_profile)
- [x] AGENTS.md enriched with knowledge catalog + trigger conditions for 20 reference files
- [x] All reference docs converted to markdown (PDFs, HTML, JSX, docx removed)
- [x] Bot auto-restarts via start.sh (launchd-managed)
- [x] Haiku/Sonnet model routing — simple queries go to Haiku (fast/cheap), complex queries to Sonnet
- [x] Model routing verified end-to-end (classifier + live API calls to both models)

### Not Yet Done
- [ ] Test reference-aware behavior in Telegram (content drafting, outreach questions, visibility queries)
- [ ] Consider writing custom tools (extend `antidote/tools/`) for LearnWell-specific workflows

## Bugs Fixed (2026-02-26)

### 1. Invalid OpenRouter model ID
- **Error:** `anthropic/claude-sonnet-4-20250514 is not a valid model ID`
- **Cause:** Config used Anthropic's direct API model ID format instead of OpenRouter's
- **Fix:** Changed `~/.antidote/config.json` model from `anthropic/claude-sonnet-4-20250514` to `anthropic/claude-sonnet-4`

### 2. Tool call format mismatch (orphaned tool_result blocks)
- **Error:** `unexpected tool_use_id found in tool_result blocks`
- **Cause:** `_parse_tool_calls()` in `openrouter.py` flattened tool calls to `{"id", "name", "arguments"}` but LiteLLM requires the OpenAI nested format `{"id", "type", "function": {"name", "arguments"}}` to correctly convert to Anthropic's `tool_use` blocks
- **Fix:** Updated `_format_messages()` in `antidote/antidote/providers/openrouter.py` to reconstruct the proper OpenAI tool_calls format before sending to LiteLLM. Added `import json`.
- **File:** `antidote/antidote/providers/openrouter.py` (lines 47-70)

### 3. Invalid OpenRouter Haiku model ID
- **Error:** `anthropic/claude-haiku-4-5-20251001 is not a valid model ID`
- **Cause:** Used Anthropic's direct API model ID format; OpenRouter uses `anthropic/claude-haiku-4.5`
- **Fix:** Updated `config.py` DEFAULTS and `~/.antidote/config.json` to `anthropic/claude-haiku-4.5`

## Configuration Summary

| Setting | Value |
|---------|-------|
| Bot name | AntidoteBot |
| Default provider | OpenRouter |
| Default model | `anthropic/claude-sonnet-4` |
| Fast model (routing) | `anthropic/claude-haiku-4.5` |
| Model routing | Enabled — heuristic classifier routes simple→Haiku, complex→Sonnet |
| Fallback provider | Ollama (`llama3.2` at localhost:11434) |
| Memory DB | `~/.antidote/memory.db` |
| Max context memories | 10 |
| Command timeout | 60s |

## Workspace (Consolidated 2026-02-27)

Single source of truth: `antidote/workspace/` (63 total repo files, 20 workspace files)

`~/.antidote/workspace` is a **symlink** → `~/webdev/github/antidote/antidote/workspace/`
`config.json` workspace path points to the repo workspace.

Both identity loading (`context.py`) and tool sandbox (`read_file`, `list_directory`) now resolve to the same directory. No manual sync required.

```
workspace/
├── SOUL.md              # Personality + writing voice (2.8KB)
├── AGENTS.md            # Behavior rules + knowledge catalog (2.6KB)
├── USER.md              # Preferences + personality profile (1.8KB)
├── MEMORY.md            # Bootstrap facts
├── About_BR/            # Bill's profile and writing style (2 files, 113KB)
├── About_Projects/      # LearnWell business and campaigns (5 files, 113KB)
├── reference/           # Quick-reference docs (4 files, 4KB)
├── projects/            # Current work (2 files, 0.9KB)
└── templates/           # Reusable templates (3 files)
```

Identity files total ~7.2KB (~1,800 tokens of 8,000 budget). Reference files (193KB on disk) cost zero tokens unless the bot reads them via tool call.

## Key Paths

| Path | Purpose |
|------|---------|
| `~/webdev/github/antidote/` | Wrapper dir (start.sh, check-upstream.sh, project-state.md) |
| `~/webdev/github/antidote/antidote/` | Git repo (.git, .venv, pyproject.toml, wizard.py) |
| `~/webdev/github/antidote/antidote/antidote/` | Python package (the code) |
| `~/webdev/github/antidote/antidote/workspace/` | **Single workspace** — identity, reference docs, projects, templates |
| `~/.antidote/config.json` | Runtime config (created by wizard) |
| `~/.antidote/memory.db` | SQLite FTS5 memory database |
| `~/.antidote/workspace` | **Symlink** → repo workspace (backward compat) |

## Architecture (Quick Reference)

```
You (Telegram) → TelegramChannel → AgentLoop → Provider (OpenRouter/Ollama)
                                      ↕              ↕
                                  ToolRegistry    LLM Response
                                      ↕              ↕
                                  MemoryStore    Tool Calls? → Execute → Loop (max 5 rounds)
```

## Dependencies

LiteLLM, python-telegram-bot, aiosqlite, cryptography (Fernet), Rich, questionary, python-dotenv

## Telegram Bot Details

| Field | Value |
|-------|-------|
| Bot name | antidote-bot |
| Username | `@antidote_br_dev_bot` |
| Direct link | https://t.me/antidote_br_dev_bot |
| Chat ID (Bill) | `7747400769` |

## Next Session Pickup

### Start the bot
```bash
cd ~/webdev/github/antidote && source antidote/.venv/bin/activate && antidote
```

### Verification tests
1. "Draft a LinkedIn post about delegation styles" → bot should read writeprint file, use Bill's voice
2. "Which communities should I engage with first?" → bot should read visibility plan
3. "What's the MMP-AI outreach sequence?" → bot should read outreach file

### What to do next
1. Test reference-aware behavior with the verification prompts above
2. Consider writing custom tools (extend `antidote/tools/`) for LearnWell-specific workflows
3. Keep workspace content updated — edit files directly in `antidote/workspace/`, no sync needed
