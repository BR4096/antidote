"""Command safety checker and audit logger.

Prevents the AI from running dangerous shell commands by checking
against a configurable blocklist, blocking path traversal beyond
the workspace, and enforcing command timeouts.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

# Default blocklist used when config is not yet loaded
DEFAULT_BLOCKED_COMMANDS = [
    "rm -rf /",
    "mkfs",
    "dd if=",
    "shutdown",
    "reboot",
    "> /dev/sd",
]
DEFAULT_MAX_TIMEOUT = 60

AUDIT_LOG_PATH = os.path.expanduser("~/.antidote/audit.log")

# Set up a dedicated file logger for the audit trail
_audit_logger: logging.Logger | None = None


def _get_audit_logger() -> logging.Logger:
    """Lazily initialise the audit file logger."""
    global _audit_logger
    if _audit_logger is not None:
        return _audit_logger

    os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
    logger = logging.getLogger("antidote.audit")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.FileHandler(AUDIT_LOG_PATH)
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        )
        logger.addHandler(handler)
    _audit_logger = logger
    return logger


def audit_log(action: str, detail: str) -> None:
    """Write an entry to the audit log."""
    logger = _get_audit_logger()
    logger.info("%s | %s", action, detail)


def is_safe(
    command: str,
    *,
    blocked_commands: list[str] | None = None,
    workspace: str | None = None,
    max_timeout: int | None = None,
) -> tuple[bool, str | None]:
    """Check whether a shell command is safe to execute.

    Returns:
        (True, None) if the command is safe.
        (False, reason) if the command should be blocked.
    """
    if blocked_commands is None:
        blocked_commands = DEFAULT_BLOCKED_COMMANDS
    if workspace is None:
        workspace = os.path.expanduser("~/.antidote/workspace")
    if max_timeout is None:
        max_timeout = DEFAULT_MAX_TIMEOUT

    # Normalise for comparison
    cmd_lower = command.lower().strip()

    # 1. Check against blocklist (substring match)
    for blocked in blocked_commands:
        if blocked.lower() in cmd_lower:
            reason = f"Blocked command pattern: '{blocked}'"
            audit_log("BLOCKED", f"cmd='{command}' reason='{reason}'")
            return False, reason

    # 2. Block path traversal beyond workspace
    resolved_workspace = os.path.realpath(os.path.expanduser(workspace))
    if "../" in command:
        # Attempt to resolve the traversal relative to workspace
        # We check if any ".." path segment in the command could escape workspace
        parts = command.split()
        for part in parts:
            if "../" in part or part == "..":
                try:
                    # Try to resolve relative to workspace
                    candidate = os.path.realpath(
                        os.path.join(resolved_workspace, part)
                    )
                    if not candidate.startswith(resolved_workspace):
                        reason = f"Path traversal beyond workspace: '{part}'"
                        audit_log("BLOCKED", f"cmd='{command}' reason='{reason}'")
                        return False, reason
                except (ValueError, OSError):
                    reason = f"Suspicious path traversal: '{part}'"
                    audit_log("BLOCKED", f"cmd='{command}' reason='{reason}'")
                    return False, reason

    # Command is considered safe
    audit_log("ALLOWED", f"cmd='{command}'")
    return True, None


def get_timeout(max_timeout: int | None = None) -> int:
    """Return the configured command timeout in seconds."""
    return max_timeout if max_timeout is not None else DEFAULT_MAX_TIMEOUT
