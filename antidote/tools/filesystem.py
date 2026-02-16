"""Filesystem tools: read_file, write_file, list_directory.

All paths are restricted to the configured workspace directory.
"""

from __future__ import annotations

import os

from antidote.config import Config
from antidote.tools.base import BaseTool, ToolResult

# Maximum file size for read_file (100KB)
MAX_READ_SIZE = 100 * 1024


def _resolve_safe_path(path: str, workspace: str) -> tuple[str, str | None]:
    """Resolve a path and verify it stays within workspace.

    Returns (resolved_path, error_message). error_message is None if safe.
    """
    workspace = os.path.realpath(os.path.expanduser(workspace))
    # Allow absolute paths or paths relative to workspace
    if os.path.isabs(path):
        resolved = os.path.realpath(path)
    else:
        resolved = os.path.realpath(os.path.join(workspace, path))

    if not resolved.startswith(workspace + os.sep) and resolved != workspace:
        return resolved, f"Path '{path}' is outside the workspace directory"

    return resolved, None


class ReadFileTool(BaseTool):
    """Read the contents of a file."""

    name = "read_file"
    description = "Read the contents of a file within the workspace. Returns the file text."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file (relative to workspace or absolute within workspace)",
            },
        },
        "required": ["path"],
    }

    def __init__(self, config: Config) -> None:
        self._workspace = config.workspace

    async def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("path", "")
        if not path:
            return ToolResult(success=False, output="", error="No path provided")

        resolved, error = _resolve_safe_path(path, self._workspace)
        if error:
            return ToolResult(success=False, output="", error=error)

        if not os.path.exists(resolved):
            return ToolResult(success=False, output="", error=f"File not found: {path}")

        if not os.path.isfile(resolved):
            return ToolResult(success=False, output="", error=f"Not a file: {path}")

        file_size = os.path.getsize(resolved)
        if file_size > MAX_READ_SIZE:
            return ToolResult(
                success=False,
                output="",
                error=f"File too large ({file_size} bytes). Max is {MAX_READ_SIZE} bytes (100KB).",
            )

        try:
            with open(resolved, "r", errors="replace") as f:
                content = f.read()
            return ToolResult(success=True, output=content)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class WriteFileTool(BaseTool):
    """Write content to a file."""

    name = "write_file"
    description = "Write content to a file within the workspace. Creates parent directories if needed."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file (relative to workspace or absolute within workspace)",
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file",
            },
        },
        "required": ["path", "content"],
    }

    def __init__(self, config: Config) -> None:
        self._workspace = config.workspace

    async def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("path", "")
        content = kwargs.get("content", "")

        if not path:
            return ToolResult(success=False, output="", error="No path provided")

        resolved, error = _resolve_safe_path(path, self._workspace)
        if error:
            return ToolResult(success=False, output="", error=error)

        try:
            os.makedirs(os.path.dirname(resolved), exist_ok=True)
            with open(resolved, "w") as f:
                f.write(content)
            return ToolResult(
                success=True,
                output=f"Written {len(content)} bytes to {path}",
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class ListDirTool(BaseTool):
    """List the contents of a directory."""

    name = "list_directory"
    description = "List files and folders in a directory within the workspace, with sizes."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the directory (relative to workspace or absolute within workspace). Defaults to workspace root.",
            },
        },
        "required": [],
    }

    def __init__(self, config: Config) -> None:
        self._workspace = config.workspace

    async def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("path", ".")

        resolved, error = _resolve_safe_path(path, self._workspace)
        if error:
            return ToolResult(success=False, output="", error=error)

        if not os.path.exists(resolved):
            return ToolResult(success=False, output="", error=f"Directory not found: {path}")

        if not os.path.isdir(resolved):
            return ToolResult(success=False, output="", error=f"Not a directory: {path}")

        try:
            entries = []
            for entry in sorted(os.listdir(resolved)):
                full_path = os.path.join(resolved, entry)
                if os.path.isdir(full_path):
                    entries.append(f"  {entry}/")
                else:
                    size = os.path.getsize(full_path)
                    entries.append(f"  {entry}  ({_human_size(size)})")

            if not entries:
                return ToolResult(success=True, output="(empty directory)")

            return ToolResult(success=True, output="\n".join(entries))
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


def _human_size(num_bytes: int) -> str:
    """Format bytes into human-readable size."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num_bytes) < 1024:
            return f"{num_bytes:.0f} {unit}" if unit == "B" else f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"
