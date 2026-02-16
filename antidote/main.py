"""Antidote entry point.

Wires all components together (Config, Provider, Memory, Tools, Context,
AgentLoop, TelegramChannel) and runs the bot with graceful shutdown on
SIGINT / SIGTERM.

Usage:
    antidote          # run the bot (auto-launches wizard if no config)
    antidote setup    # run the setup wizard
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import signal
import sys

BANNER = r"""[bold green]
    _   _  _ _____ ___ ___  ___ _____ ___
   /_\ | \| |_   _|_ _|   \/ _ \_   _| __|
  / _ \| .` | | |  | || |) | (_) || | | _|
 /_/ \_\_|\_| |_| |___|___/ \___/ |_| |___|[/bold green]"""

TAGLINES = [
    "The antidote to bloated AI frameworks.",
    "Less framework. More you.",
    "Your AI. Your Mac. Your rules.",
    "One Telegram message away from useful.",
    "No Docker. No cloud. No nonsense.",
    "All the power. None of the YAML.",
    "AI that remembers you. Runs on your Mac. Talks on Telegram.",
    "Encrypted at rest. Opinionated in conversation.",
    "Small enough to read. Powerful enough to matter.",
]

CONFIG_PATH = os.path.expanduser("~/.antidote/config.json")


def _print_banner() -> None:
    try:
        from rich.console import Console
        c = Console()
        c.print(BANNER)
        c.print(f"  [dim]{random.choice(TAGLINES)}[/dim]\n")
    except ImportError:
        print("\n  ANTIDOTE")
        print(f"  {random.choice(TAGLINES)}\n")


def _run_wizard() -> None:
    """Import and run the setup wizard."""
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    wizard_path = os.path.join(script_dir, "wizard.py")

    if os.path.exists(wizard_path):
        # Run wizard as a module
        import importlib.util
        spec = importlib.util.spec_from_file_location("wizard", wizard_path)
        wizard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(wizard)
        wizard.run()
    else:
        print(f"  Wizard not found at {wizard_path}")
        print("  Set env vars manually:")
        print("    export OPENROUTER_API_KEY=your-key")
        print("    export TELEGRAM_BOT_TOKEN=your-token")
        sys.exit(1)


async def main() -> None:
    from antidote.config import Config
    from antidote.providers import get_provider
    from antidote.memory.store import MemoryStore
    from antidote.tools.registry import ToolRegistry
    from antidote.tools.filesystem import ReadFileTool, WriteFileTool, ListDirTool
    from antidote.tools.shell import RunCommandTool
    from antidote.agent.context import ContextBuilder
    from antidote.agent.loop import AgentLoop
    from antidote.channels.telegram import TelegramChannel

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )
    logger = logging.getLogger("antidote")

    config = Config()

    # --- Provider ---
    provider = get_provider()

    # --- Memory ---
    memory = MemoryStore(config.memory.db_path)
    await memory.initialize()

    # --- Tools ---
    tools = ToolRegistry()
    tools.register(ReadFileTool(config))
    tools.register(WriteFileTool(config))
    tools.register(ListDirTool(config))
    tools.register(RunCommandTool(config))

    # --- Agent ---
    context = ContextBuilder(config, memory, tools)
    agent = AgentLoop(provider, context, memory, tools)

    # --- Telegram ---
    telegram = TelegramChannel(config)

    # --- Graceful shutdown ---
    shutdown_event = asyncio.Event()

    def _request_shutdown() -> None:
        logger.info("Shutdown signal received")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _request_shutdown)

    _print_banner()
    logger.info("Antidote is running. Send a message on Telegram.")
    await telegram.start(on_message=agent.process_message)

    # Block until shutdown is requested
    await shutdown_event.wait()

    logger.info("Shutting down gracefully...")
    await telegram.stop()
    await memory.close()
    logger.info("Goodbye.")


def cli() -> None:
    """Entry point: `antidote` or `antidote setup`"""
    # Handle subcommands
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        _run_wizard()
        return

    # Auto-launch wizard if no config exists
    if not os.path.exists(CONFIG_PATH):
        _print_banner()
        print("  No configuration found. Starting setup wizard...\n")
        _run_wizard()
        # After wizard, ask if they want to start
        try:
            answer = input("  Start Antidote now? [Y/n] ").strip().lower()
            if answer in ("", "y", "yes"):
                pass  # fall through to main()
            else:
                print("\n  Run `antidote` when you're ready.")
                return
        except (KeyboardInterrupt, EOFError):
            print()
            return

    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except ValueError as e:
        print(f"\n  Error: {e}")
        print("\n  Run `antidote setup` to reconfigure.\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n  Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
