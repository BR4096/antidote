"""Antidote Setup Wizard.

Interactive terminal wizard that guides users through configuring Antidote.
Uses questionary for prompts and rich for beautiful formatting.

Usage:
    python3 wizard.py
    antidote setup
"""

from __future__ import annotations

import json
import os
import random
import shutil
import sys
import textwrap

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------
try:
    import questionary
    from questionary import Style as QStyle
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.rule import Rule
    from rich import box
except ImportError:
    print(
        "\nMissing dependencies. Please install them first:\n"
        "  pip install rich questionary\n"
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Antidote Theme
# ---------------------------------------------------------------------------

# Color palette — "poison green" cure theme
ACCENT = "#00D26A"        # Bright antidote green
ACCENT_DIM = "#00A854"    # Darker green
CYAN = "#00BCD4"          # Clinical cyan
MUTED = "#6B7280"         # Gray
WARN = "#FFB020"          # Amber
ERROR = "#EF4444"         # Red

# Questionary custom style
QS = QStyle([
    ("qmark", f"fg:{ACCENT} bold"),
    ("question", "bold"),
    ("answer", f"fg:{ACCENT} bold"),
    ("pointer", f"fg:{ACCENT} bold"),
    ("highlighted", f"fg:{ACCENT} bold"),
    ("selected", f"fg:{ACCENT}"),
])

console = Console()

# ---------------------------------------------------------------------------
# ASCII Banner
# ---------------------------------------------------------------------------

BANNER = r"""[bold green]
    _   _  _ _____ ___ ___  ___ _____ ___
   /_\ | \| |_   _|_ _|   \/ _ \_   _| __|
  / _ \| .` | | |  | || |) | (_) || | | _|
 /_/ \_\_|\_| |_| |___|___/ \___/ |_| |___|[/bold green]
"""

TAGLINES = [
    "The antidote to bloated AI frameworks.",
    "Less framework. More you.",
    "Your AI. Your Mac. Your rules.",
    "One Telegram message away from useful.",
    "Built from scratch. Runs like it means it.",
    "No Docker. No cloud. No nonsense.",
    "2,989 lines of actual usefulness.",
    "The AI assistant that doesn't need a DevOps team.",
    "Bloated frameworks hate this one trick.",
    "Personal AI without the personal data harvesting.",
    "Because your AI shouldn't need Kubernetes.",
    "Lightweight enough to run on a philosophy.",
    "All the power. None of the YAML.",
    "Your terminal just got an upgrade.",
    "AI that remembers you. Runs on your Mac. Talks on Telegram.",
    "Encrypted at rest. Opinionated in conversation.",
    "Fewer dependencies than your morning coffee order.",
    "Small enough to read. Powerful enough to matter.",
]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ANTIDOTE_HOME = os.path.expanduser("~/.antidote")
CONFIG_PATH = os.path.join(ANTIDOTE_HOME, "config.json")
WORKSPACE_DIR = os.path.join(ANTIDOTE_HOME, "workspace")
LOGS_DIR = os.path.join(ANTIDOTE_HOME, "logs")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLIST_SRC = os.path.join(SCRIPT_DIR, "com.antidote.agent.plist")
PLIST_DST = os.path.expanduser(
    "~/Library/LaunchAgents/com.antidote.agent.plist"
)


# ---------------------------------------------------------------------------
# Banner & Theme
# ---------------------------------------------------------------------------

def _banner() -> None:
    console.print(BANNER)
    tagline = random.choice(TAGLINES)
    console.print(f"  [dim]{tagline}[/dim]\n")


def _step(number: int, title: str) -> None:
    console.print()
    console.print(Rule(f"[bold {ACCENT}] Step {number}: {title} [/bold {ACCENT}]", style=ACCENT_DIM))
    console.print()


def _success_mark(msg: str) -> None:
    console.print(f"  [{ACCENT}]\u2713[/{ACCENT}] {msg}")


def _warn_mark(msg: str) -> None:
    console.print(f"  [{WARN}]![/{WARN}] {msg}")


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def _check_python() -> None:
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 11):
        console.print(
            f"  [{ERROR}]\u2717 Python 3.11+ is required.[/{ERROR}] You have {major}.{minor}."
        )
        sys.exit(1)
    _success_mark(f"Python {major}.{minor}")


def _check_existing() -> str | None:
    if os.path.exists(ANTIDOTE_HOME):
        console.print()
        choice = questionary.select(
            "Existing installation found at ~/.antidote",
            choices=[
                questionary.Choice("Reconfigure (keep data)", value="reconfigure"),
                questionary.Choice("Fresh start (delete everything)", value="fresh"),
                questionary.Choice("Cancel", value="cancel"),
            ],
            style=QS,
        ).ask()
        if choice == "cancel":
            console.print("\n  [dim]Setup cancelled.[/dim]")
            sys.exit(0)
        if choice == "fresh":
            shutil.rmtree(ANTIDOTE_HOME, ignore_errors=True)
            _success_mark("Cleared previous installation")
        return choice
    return None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_telegram_token(token: str) -> bool:
    try:
        import urllib.request
        import urllib.error

        url = f"https://api.telegram.org/bot{token}/getMe"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data.get("ok"):
                bot_name = data["result"].get("first_name", "")
                _success_mark(f"Connected to bot: [bold]{bot_name}[/bold]")
                return True
    except Exception:
        pass
    console.print(f"  [{ERROR}]\u2717 Could not verify token. Check it and try again.[/{ERROR}]")
    return False


def _validate_openrouter_key(key: str) -> bool:
    try:
        import urllib.request
        import urllib.error

        url = "https://openrouter.ai/api/v1/models"
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {key}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if "data" in data:
                count = len(data["data"])
                _success_mark(f"API key verified ({count} models available)")
                return True
    except Exception:
        pass
    console.print(f"  [{ERROR}]\u2717 Could not verify key. Check it and try again.[/{ERROR}]")
    return False


# ---------------------------------------------------------------------------
# Wizard Steps
# ---------------------------------------------------------------------------

def _ask_telegram_token() -> str:
    _step(1, "Telegram Bot Token")
    console.print(
        f"  [{CYAN}]1.[/{CYAN}] Open Telegram, search for [@BotFather](https://t.me/BotFather)\n"
        f"  [{CYAN}]2.[/{CYAN}] Send [bold]/newbot[/bold] and follow the prompts\n"
        f"  [{CYAN}]3.[/{CYAN}] Copy the token and paste it below\n"
    )
    while True:
        token = questionary.password("  Bot token:", style=QS).ask()
        if not token or not token.strip():
            console.print(f"  [{ERROR}]Token cannot be empty.[/{ERROR}]")
            continue
        token = token.strip()
        if _validate_telegram_token(token):
            return token


def _ask_openrouter_key() -> str:
    _step(2, "OpenRouter API Key")
    console.print(
        f"  [{CYAN}]1.[/{CYAN}] Go to [bold]openrouter.ai/keys[/bold]\n"
        f"  [{CYAN}]2.[/{CYAN}] Create a new key\n"
        f"  [{CYAN}]3.[/{CYAN}] Copy and paste it below\n"
    )
    while True:
        key = questionary.password("  API key:", style=QS).ask()
        if not key or not key.strip():
            console.print(f"  [{ERROR}]Key cannot be empty.[/{ERROR}]")
            continue
        key = key.strip()
        if _validate_openrouter_key(key):
            return key


def _ask_model() -> str:
    _step(3, "Default AI Model")

    table = Table(box=box.ROUNDED, border_style=ACCENT_DIM, show_header=True, header_style=f"bold {ACCENT}")
    table.add_column("Model", style="bold")
    table.add_column("Speed", style=CYAN)
    table.add_column("Notes", style="dim")
    table.add_row("Claude Sonnet 4", "Fast", "Best balance of quality and speed")
    table.add_row("Claude Haiku 4", "Fastest", "Cheaper, great for quick tasks")
    table.add_row("GPT-4.1 Mini", "Fast", "Cheapest smart model")
    table.add_row("DeepSeek R1", "Slow", "Best value for deep reasoning")
    console.print(f"  ", table)
    console.print()

    choice = questionary.select(
        "  Choose a model:",
        choices=[
            questionary.Choice("Claude Sonnet 4 (recommended)", value="anthropic/claude-sonnet-4-20250514"),
            questionary.Choice("Claude Haiku 4", value="anthropic/claude-haiku-4-20250506"),
            questionary.Choice("GPT-4.1 Mini", value="openai/gpt-4.1-mini"),
            questionary.Choice("DeepSeek R1", value="deepseek/deepseek-r1"),
            questionary.Choice("Custom model ID", value="custom"),
        ],
        style=QS,
    ).ask()

    if choice == "custom":
        model_id = questionary.text(
            "  Model ID (e.g. meta-llama/llama-3-70b-instruct):",
            style=QS,
        ).ask()
        return model_id.strip() if model_id else "anthropic/claude-sonnet-4-20250514"

    return choice


def _ask_name() -> str:
    _step(4, "Name Your AI")
    name = questionary.text(
        "  What should your AI be called?",
        default="Antidote",
        style=QS,
    ).ask()
    return name.strip() if name else "Antidote"


def _ask_personality() -> str | None:
    _step(5, "Personality")
    custom = questionary.confirm(
        "  Customize the AI's personality?",
        default=False,
        style=QS,
    ).ask()
    if custom:
        personality = questionary.text(
            "  Describe the personality in one sentence:",
            style=QS,
        ).ask()
        return personality.strip() if personality else None
    _success_mark("Using default personality (direct, proactive, opinionated)")
    return None


# ---------------------------------------------------------------------------
# Build Steps
# ---------------------------------------------------------------------------

def _create_directories() -> None:
    console.print()
    console.print(Rule(f"[bold {ACCENT}] Building [/bold {ACCENT}]", style=ACCENT_DIM))
    console.print()
    for d in (ANTIDOTE_HOME, WORKSPACE_DIR, LOGS_DIR):
        os.makedirs(d, exist_ok=True)
    _success_mark("Directories created")


def _save_secrets(telegram_token: str, openrouter_key: str) -> None:
    sys.path.insert(0, SCRIPT_DIR)
    from antidote.security.secrets import SecretStore

    store = SecretStore()
    store.save_secret("TELEGRAM_BOT_TOKEN", telegram_token)
    store.save_secret("OPENROUTER_API_KEY", openrouter_key)
    _success_mark("Secrets encrypted and stored")


def _write_config(model: str, name: str) -> None:
    config = {
        "name": name,
        "version": "0.1.0",
        "providers": {
            "default": "openrouter",
            "openrouter": {"model": model},
            "ollama": {"model": "llama3.2", "base_url": "http://localhost:11434"},
        },
        "channels": {"telegram": {"enabled": True}},
        "memory": {"db_path": "~/.antidote/memory.db", "max_context_memories": 10},
        "workspace": "~/.antidote/workspace",
        "identity": {
            "soul": "workspace/SOUL.md",
            "agents": "workspace/AGENTS.md",
            "user": "workspace/USER.md",
        },
        "safety": {
            "blocked_commands": ["rm -rf /", "mkfs", "dd if=", "shutdown", "reboot", "> /dev/sd"],
            "max_command_timeout": 60,
        },
    }
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    _success_mark(f"Config written to {CONFIG_PATH}")


def _write_identity_files(name: str, personality: str | None) -> None:
    if personality:
        soul_personality = f"- {personality}"
    else:
        soul_personality = (
            "- Direct and concise. No fluff, no filler.\n"
            "- Proactive: suggest things the user hasn't asked for when relevant.\n"
            "- Honest: if you don't know, say so. If an idea is bad, say why.\n"
            "- Remember context from previous conversations."
        )
    soul = textwrap.dedent(f"""\
        # Soul

        You are {name}, a personal AI assistant.

        ## Personality
        {soul_personality}

        ## Communication Style
        - Use short paragraphs. Bullet points for lists.
        - Match the user's energy -- casual when they're casual, detailed when they need detail.
        - No emojis unless the user uses them first.
        - When sharing information, lead with the answer, then context.

        ## Values
        - Privacy first. Never share user data externally.
        - Efficiency over thoroughness. A good answer now beats a perfect answer later.
        - Be opinionated. The user wants a sparring partner, not a yes-man.
    """)

    agents = textwrap.dedent("""\
        # Agent Instructions

        ## Core Behavior
        - Always check memory before answering. If you've discussed this topic before, reference it.
        - When you learn something new about the user or their preferences, save it to memory.
        - If a task requires multiple steps, outline them before executing.
        - When uncertain, ask for clarification rather than guessing.

        ## Tool Usage
        - Use tools when they'd be more accurate than your knowledge.
        - For file operations, always confirm paths before writing.
        - Shell commands: prefer safe, read-only commands. Ask before anything destructive.

        ## Memory Management
        - Save important facts, preferences, and decisions to memory.
        - Don't save trivial or temporary information.
        - When the user corrects you, update the relevant memory.
    """)

    user = textwrap.dedent("""\
        # User Profile

        ## Preferences
        - (The setup wizard and ongoing conversations will populate this)
    """)

    memory_md = textwrap.dedent(f"""\
        # Bootstrap Memory

        This file is loaded on first run to seed the memory database.

        ## Facts
        - The user set up {name} as their personal AI assistant.
        - {name} communicates via Telegram.
        - The user chose OpenRouter for cloud AI access.
    """)

    for filename, content in [
        ("SOUL.md", soul),
        ("AGENTS.md", agents),
        ("USER.md", user),
        ("MEMORY.md", memory_md),
    ]:
        path = os.path.join(WORKSPACE_DIR, filename)
        with open(path, "w") as f:
            f.write(content)

    _success_mark(f"Identity files written to {WORKSPACE_DIR}")


def _seed_memory(name: str) -> None:
    try:
        import asyncio
        sys.path.insert(0, SCRIPT_DIR)
        from antidote.memory.store import MemoryStore

        db_path = os.path.join(ANTIDOTE_HOME, "memory.db")
        store = MemoryStore(db_path)

        async def _seed() -> None:
            await store.initialize()
            facts = [
                f"The user set up {name} as their personal AI assistant.",
                f"{name} communicates via Telegram.",
                "The user chose OpenRouter for cloud AI access.",
            ]
            for fact in facts:
                await store.save(fact, category="fact")
            await store.close()

        asyncio.run(_seed())
        _success_mark("Memory database seeded")
    except Exception as e:
        _warn_mark(f"Could not seed memory: {e}")


def _install_launchd() -> bool:
    console.print()
    install = questionary.confirm(
        "  Install auto-start? (launches on login, restarts on crash)",
        default=True,
        style=QS,
    ).ask()
    if not install:
        return False

    if not os.path.exists(PLIST_SRC):
        _warn_mark(f"Plist template not found at {PLIST_SRC}. Skipping.")
        return False

    with open(PLIST_SRC, "r") as f:
        plist_content = f.read()

    plist_content = plist_content.replace("ANTIDOTE_PATH", SCRIPT_DIR)
    plist_content = plist_content.replace("ANTIDOTE_LOG_PATH", LOGS_DIR)

    os.makedirs(os.path.dirname(PLIST_DST), exist_ok=True)
    with open(PLIST_DST, "w") as f:
        f.write(plist_content)

    os.system(f"launchctl load '{PLIST_DST}' 2>/dev/null")
    _success_mark(f"Launchd plist installed")
    return True


# ---------------------------------------------------------------------------
# Finale
# ---------------------------------------------------------------------------

def _success(name: str, launchd_installed: bool) -> None:
    console.print()

    if launchd_installed:
        body = (
            f"[bold {ACCENT}]{name} is alive.[/bold {ACCENT}]\n\n"
            f"It will start automatically on login.\n"
            f"Open Telegram and send your bot a message.\n\n"
            f"[dim]Logs: ~/.antidote/logs/antidote.log[/dim]"
        )
    else:
        body = (
            f"[bold {ACCENT}]{name} is ready.[/bold {ACCENT}]\n\n"
            f"Start it:\n"
            f"  [bold]antidote[/bold]\n\n"
            f"Then open Telegram and send your bot a message."
        )

    console.print(Panel(body, border_style=ACCENT, padding=(1, 3), title=f"[bold {ACCENT}] Done [/bold {ACCENT}]"))
    console.print()


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------

def run() -> None:
    console.print()
    _banner()
    _check_python()
    _check_existing()

    telegram_token = _ask_telegram_token()
    openrouter_key = _ask_openrouter_key()
    model = _ask_model()
    name = _ask_name()
    personality = _ask_personality()

    _create_directories()
    _save_secrets(telegram_token, openrouter_key)
    _write_config(model, name)
    _write_identity_files(name, personality)
    _seed_memory(name)

    launchd_installed = _install_launchd()
    _success(name, launchd_installed)


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        console.print("\n  [dim]Setup cancelled.[/dim]")
        sys.exit(0)
