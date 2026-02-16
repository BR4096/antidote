"""Shell command execution tool with safety checks.

Executes commands via asyncio subprocess, enforces timeouts, checks
the safety blocklist before running, and truncates large output.
"""

from __future__ import annotations

import asyncio
import logging

from antidote.config import Config
from antidote.security.safety import is_safe, get_timeout
from antidote.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

# Maximum output size (10KB)
MAX_OUTPUT_SIZE = 10 * 1024


class RunCommandTool(BaseTool):
    """Execute a shell command and return its output."""

    name = "run_command"
    description = (
        "Execute a shell command on the local machine. "
        "Returns stdout and stderr. Dangerous commands are blocked."
    )
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute",
            },
        },
        "required": ["command"],
    }

    def __init__(self, config: Config) -> None:
        self._config = config
        safety = config.safety
        self._blocked_commands = safety.to_dict().get(
            "blocked_commands", []
        ) if hasattr(safety, "to_dict") else []
        self._workspace = config.workspace
        self._max_timeout = safety.to_dict().get(
            "max_command_timeout", 60
        ) if hasattr(safety, "to_dict") else 60

    async def execute(self, **kwargs) -> ToolResult:
        command = kwargs.get("command", "")
        if not command:
            return ToolResult(success=False, output="", error="No command provided")

        # Safety check
        safe, reason = is_safe(
            command,
            blocked_commands=self._blocked_commands,
            workspace=self._workspace,
            max_timeout=self._max_timeout,
        )
        if not safe:
            return ToolResult(
                success=False,
                output="",
                error=f"Command blocked: {reason}",
            )

        timeout = get_timeout(self._max_timeout)

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self._workspace,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Command timed out after {timeout} seconds",
                )

            # Decode output
            stdout_text = stdout.decode("utf-8", errors="replace") if stdout else ""
            stderr_text = stderr.decode("utf-8", errors="replace") if stderr else ""

            # Combine output
            output_parts = []
            if stdout_text:
                output_parts.append(stdout_text)
            if stderr_text:
                output_parts.append(f"[stderr]\n{stderr_text}")

            output = "\n".join(output_parts)

            # Truncate if too large
            if len(output) > MAX_OUTPUT_SIZE:
                output = output[:MAX_OUTPUT_SIZE] + "\n... [output truncated at 10KB]"

            success = process.returncode == 0
            error = None if success else f"Exit code: {process.returncode}"

            return ToolResult(success=success, output=output, error=error)

        except Exception as e:
            logger.exception("Error executing command: %s", command)
            return ToolResult(success=False, output="", error=str(e))
