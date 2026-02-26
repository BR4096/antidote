# Antidote — Project State

**Last updated:** 2026-02-26
**Repo:** `/Users/billringle/webdev/github/antidote/`

## What Is Antidote

Personal AI assistant built in Python (~3,000 lines). Runs on Mac, talks via Telegram, remembers everything via SQLite FTS5. Uses OpenRouter for 100+ LLM models. Built by Mark Kashef.

## Current Status: Running and Verified

### Done
- [x] Repo cloned to `~/webdev/github/antidote/`
- [x] Python 3.14 detected and compatible
- [x] Virtual environment created at `antidote/.venv/`
- [x] All dependencies installed via `pip install -e .`
- [x] Setup wizard completed — config written to `~/.antidote/config.json`
- [x] Memory database seeded at `~/.antidote/memory.db`
- [x] Workspace identity files in place (`SOUL.md`, `AGENTS.md`, `USER.md`, `MEMORY.md`)
- [x] Bot running and responding to Telegram messages
- [x] Tool calls (memory search) verified working
- [x] OpenRouter credits added and billing confirmed

- [x] Identity files customized for Bill (SOUL.md, USER.md, AGENTS.md)
- [x] Runtime workspace synced (`~/.antidote/workspace/`)

### Not Yet Done
- [ ] (Optional) Install launchd plist for auto-restart on crash
- [ ] Test customized personality in Telegram conversation
- [ ] Explore adding custom tools or expanding workspace content

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

## Configuration Summary

| Setting | Value |
|---------|-------|
| Bot name | AntidoteBot |
| Default provider | OpenRouter |
| Default model | `anthropic/claude-sonnet-4` |
| Fallback provider | Ollama (`llama3.2` at localhost:11434) |
| Memory DB | `~/.antidote/memory.db` |
| Max context memories | 10 |
| Command timeout | 60s |

## Key Paths

| Path | Purpose |
|------|---------|
| `~/webdev/github/antidote/` | Repo root (pyproject.toml, wizard.py, start.sh) |
| `~/webdev/github/antidote/antidote/` | Git dir + .venv + Python package |
| `~/webdev/github/antidote/workspace/` | Identity stack (SOUL, AGENTS, USER, MEMORY) |
| `~/.antidote/config.json` | Runtime config (created by wizard) |
| `~/.antidote/memory.db` | SQLite FTS5 memory database |
| `~/.antidote/workspace/` | Runtime workspace copy |

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

### What to do next
1. Test the customized personality — send a few messages and see if the tone feels right
2. (Optional) Install launchd plist for always-on background running:
   ```bash
   cp com.antidote.agent.plist ~/Library/LaunchAgents/
   launchctl load ~/Library/LaunchAgents/com.antidote.agent.plist
   ```
3. Explore adding workspace content (reference docs, project notes) for the bot to read
4. Consider writing custom tools (extend `antidote/tools/`) for LearnWell-specific workflows
