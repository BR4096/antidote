<p align="center">
  <br>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://img.shields.io/badge/ANTIDOTE-00D26A?style=for-the-badge&logoColor=white&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiPjxwYXRoIGQ9Ik0xMiAydjIwbTAtMTBsNi02bS02IDZsLTYtNiIvPjwvc3ZnPg==">
    <img alt="Antidote" src="https://img.shields.io/badge/ANTIDOTE-00D26A?style=for-the-badge&logoColor=white">
  </picture>
  <br>
</p>

<h3 align="center">The antidote to bloated AI frameworks.</h3>

<p align="center">
  A purpose-built Python AI assistant for personal use.<br>
  Runs on Mac. Talks via Telegram. Remembers everything.<br>
  Built from scratch. ~3,000 lines. Ships today.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-00D26A?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/telegram-bot_api-0088cc?style=flat-square&logo=telegram&logoColor=white" alt="Telegram">
  <img src="https://img.shields.io/badge/100+_models-OpenRouter-8B5CF6?style=flat-square" alt="OpenRouter">
  <img src="https://img.shields.io/badge/memory-SQLite_FTS5-003B57?style=flat-square&logo=sqlite&logoColor=white" alt="SQLite FTS5">
  <img src="https://img.shields.io/badge/secrets-Fernet_encrypted-EF4444?style=flat-square&logo=letsencrypt&logoColor=white" alt="Encrypted">
</p>

---

```
    _   _  _ _____ ___ ___  ___ _____ ___
   /_\ | \| |_   _|_ _|   \/ _ \_   _| __|
  / _ \| .` | | |  | || |) | (_) || | | _|
 /_/ \_\_|\_| |_| |___|___/ \___/ |_| |___|

  Less framework. More you.
```

---

## What is this

Antidote is a personal AI assistant that:

- **Talks to you on Telegram** — no web UI, no dashboard, just message your bot
- **Remembers everything** — SQLite FTS5 full-text search memory that persists across restarts
- **Uses any model** — 100+ models via OpenRouter (Claude, GPT, DeepSeek, Llama, etc.)
- **Runs on your Mac** — always on, auto-restarts on crash via launchd
- **Has tools** — reads/writes files, runs shell commands, searches memory
- **Encrypts your secrets** — API keys stored with Fernet encryption tied to your hardware
- **Has a personality** — configurable soul, behavior rules, and user preferences in markdown

## What it is NOT

- Not a framework. Not a library. Not a platform.
- No Docker. No Kubernetes. No YAML configs.
- No multi-user auth. No web dashboard. No cloud deployment.
- No vector databases. No embeddings. No RAG pipelines.
- Just an AI assistant that works.

## Quickstart

```bash
# Clone and enter
git clone <this-repo>
cd antidote

# One command to set up and run
./start.sh
```

The setup wizard walks you through everything:

```
 ✓ Python 3.11
 ─── Step 1: Telegram Bot Token ───
 ─── Step 2: OpenRouter API Key ───
 ─── Step 3: Default AI Model ───
 ─── Step 4: Name Your AI ───
 ─── Step 5: Personality ───
 ─── Building ───
 ✓ Secrets encrypted and stored
 ✓ Config written
 ✓ Identity files written
 ✓ Memory database seeded
 ╭─ Done ─╮
 │ Antidote is ready. │
 ╰────────╯
```

After setup, just:

```bash
antidote
```

## Architecture

```
antidote/
├── antidote/
│   ├── main.py              # Entry point — wires everything
│   ├── config.py             # Singleton config with dot-access
│   ├── agent/
│   │   ├── loop.py           # Core brain — LLM + tool loop (max 5 rounds)
│   │   └── context.py        # System prompt builder (identity + memory)
│   ├── providers/
│   │   ├── base.py           # Provider ABC + dataclasses
│   │   ├── openrouter.py     # 100+ models via LiteLLM
│   │   └── ollama.py         # Local LLM fallback (free, private)
│   ├── channels/
│   │   └── telegram.py       # Long-polling, typing indicator, markdown
│   ├── memory/
│   │   └── store.py          # SQLite FTS5 with bm25 ranking
│   ├── tools/
│   │   ├── registry.py       # Tool discovery and registration
│   │   ├── filesystem.py     # read_file, write_file, list_directory
│   │   └── shell.py          # run_command (with safety blocklist)
│   └── security/
│       ├── secrets.py        # Fernet encryption (hardware UUID key)
│       └── safety.py         # Command blocklist + audit log
├── workspace/
│   ├── SOUL.md               # AI personality + writing voice
│   ├── AGENTS.md             # Behavior rules + knowledge catalog
│   ├── USER.md               # Your preferences + personality profile
│   ├── MEMORY.md             # Bootstrap facts
│   ├── About_BR/             # User profile docs (personality, writing style)
│   ├── About_Projects/       # Business docs (company profile, campaigns, outreach)
│   ├── reference/            # Quick-reference docs (ICP, stack conventions, calendar)
│   ├── projects/             # Current sprint + quarterly goals
│   └── templates/            # Reusable templates (proposals, emails, evaluations)
├── wizard.py                 # Interactive setup wizard
├── start.sh                  # One-command launcher
└── com.antidote.agent.plist  # macOS auto-restart
```

## How it works

```
You (Telegram) → TelegramChannel → AgentLoop → Provider (OpenRouter/Ollama)
                                      ↕              ↕
                                  ToolRegistry    LLM Response
                                      ↕              ↕
                                  MemoryStore    Tool Calls?
                                                     ↕
                                              Execute → Loop back
                                                  (max 5 rounds)
```

1. You send a Telegram message
2. The context builder assembles: personality + relevant memories + conversation history
3. The LLM responds, optionally calling tools (file ops, shell, memory)
4. Tool results feed back into the LLM for up to 5 rounds
5. Final response goes back to Telegram
6. Conversation summary saved to memory

## The Identity Stack

Antidote's personality is defined in markdown files you can edit:

| File | Purpose |
|------|---------|
| `SOUL.md` | Who the AI is — personality, communication style, values |
| `AGENTS.md` | How it behaves — when to use tools, how to manage memory |
| `USER.md` | Who you are — preferences, populated over time |
| `MEMORY.md` | Bootstrap facts — seeded on first run |

## Memory

SQLite FTS5 full-text search. No embeddings. No vector DB. No API costs for recall.

- **Save**: Auto-deduplicates (>80% word overlap → update instead of insert)
- **Search**: BM25 ranking via FTS5 `MATCH`
- **Recall**: Agent automatically searches memory on every message
- **Built-in tools**: The LLM can `save_memory`, `search_memory`, `forget_memory`

## Security

- **Encrypted secrets**: API keys encrypted with Fernet, key derived from your Mac's hardware UUID
- **Command blocklist**: Prevents `rm -rf /`, `mkfs`, `dd`, `shutdown`, etc.
- **Path restriction**: File tools restricted to workspace directory
- **Audit log**: All shell commands logged to `~/.antidote/audit.log`
- **Timeout enforcement**: Shell commands killed after 60s (configurable)

## Commands

```bash
antidote          # Run the bot (auto-setup if first time)
antidote setup    # Run/re-run the setup wizard
./start.sh        # Alternative launcher (creates venv if needed)
```

## Configuration

Generated by the wizard at `~/.antidote/config.json`:

```json
{
  "name": "Antidote",
  "providers": {
    "default": "openrouter",
    "openrouter": { "model": "anthropic/claude-sonnet-4-20250514" },
    "ollama": { "model": "llama3.2", "base_url": "http://localhost:11434" }
  },
  "memory": { "db_path": "~/.antidote/memory.db", "max_context_memories": 10 },
  "safety": { "blocked_commands": ["rm -rf /", "mkfs", "dd if=", ...] }
}
```

## Requirements

- Python 3.11+
- macOS (for hardware UUID encryption + launchd auto-restart)
- A Telegram account + bot token (free, 2 minutes via @BotFather)
- An OpenRouter API key (pay-per-use, most models under $0.01/message)

## Built with

| Dependency | Purpose |
|-----------|---------|
| [LiteLLM](https://github.com/BerriAI/litellm) | Unified API for 100+ LLM providers |
| [python-telegram-bot](https://python-telegram-bot.org/) | Async Telegram Bot API |
| [aiosqlite](https://github.com/omnilib/aiosqlite) | Async SQLite with FTS5 |
| [cryptography](https://cryptography.io/) | Fernet encryption for secrets |
| [Rich](https://github.com/Textualize/rich) | Beautiful terminal formatting |
| [questionary](https://github.com/tmbo/questionary) | Interactive CLI prompts |

## Stats

```
~3,000 lines  ·  63 files  ·  7 dependencies  ·  0 Docker containers
```

---

<p align="center">
  <sub>Built by <a href="https://github.com/marwankashef">Mark Kashef</a> as the antidote to everything wrong with AI frameworks.</sub>
</p>
