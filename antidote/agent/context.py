"""Context builder for the Antidote agent.

Assembles the system prompt from identity files (SOUL.md, AGENTS.md, USER.md),
relevant memories, and tool descriptions. Also manages conversation context
with memory augmentation and token budget truncation.
"""

from __future__ import annotations

import os
from pathlib import Path

from antidote.config import Config
from antidote.memory.store import MemoryStore
from antidote.providers.base import Message, ToolDefinition


# Rough token estimation: ~4 chars per token on average
_CHARS_PER_TOKEN = 4
_MAX_CONTEXT_TOKENS = 8000
_MAX_CONTEXT_CHARS = _MAX_CONTEXT_TOKENS * _CHARS_PER_TOKEN


def _read_identity_file(path: str) -> str:
    """Read an identity markdown file, returning empty string if missing."""
    expanded = os.path.expanduser(path)
    try:
        return Path(expanded).read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


class ContextBuilder:
    """Builds system prompts and conversation contexts for the agent.

    Usage:
        ctx = ContextBuilder(config, memory, tools)
        system_prompt = await ctx.build_system_prompt()
        messages = await ctx.build_conversation_context(history, query)
    """

    def __init__(
        self,
        config: Config,
        memory: MemoryStore,
        tools: object | None = None,
    ) -> None:
        self._config = config
        self._memory = memory
        self._tools = tools  # ToolRegistry instance

    def _resolve_identity_path(self, relative_path: str) -> str:
        """Resolve an identity file path relative to the project workspace dir."""
        # Identity paths in config are relative like "workspace/SOUL.md"
        # Resolve relative to the antidote project root
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base, relative_path)

    async def build_system_prompt(self) -> str:
        """Build the full system prompt from identity files, memories, and tools.

        Reads and concatenates:
        1. SOUL.md (personality)
        2. AGENTS.md (behavior rules)
        3. USER.md (user preferences)
        4. Recent memories (last N from memory store)
        5. Available tools list
        """
        parts: list[str] = []

        # 1-3. Identity files
        identity = self._config.identity
        for label, path_key in [
            ("Personality", identity.get("soul", "workspace/SOUL.md")),
            ("Instructions", identity.get("agents", "workspace/AGENTS.md")),
            ("User Profile", identity.get("user", "workspace/USER.md")),
        ]:
            content = _read_identity_file(self._resolve_identity_path(path_key))
            if content.strip():
                parts.append(content.strip())

        # 4. Recent memories
        max_memories = self._config.memory.get("max_context_memories", 10)
        recent = await self._memory.recent(limit=max_memories)
        if recent:
            memory_lines = ["## Recent Knowledge"]
            for mem in recent:
                memory_lines.append(f"- [{mem.category}] {mem.content}")
            parts.append("\n".join(memory_lines))

        # 5. Available tools
        if self._tools is not None and hasattr(self._tools, "all"):
            tool_list = self._tools.all()
            if tool_list:
                tool_lines = ["## Available Tools"]
                for tool in tool_list:
                    tool_lines.append(f"- **{tool.name}**: {tool.description}")
                parts.append("\n".join(tool_lines))

        return "\n\n---\n\n".join(parts)

    async def build_conversation_context(
        self,
        messages: list[Message],
        query: str,
    ) -> list[Message]:
        """Build the full message list for an LLM call.

        1. Builds system prompt
        2. Searches memory for relevant entries matching the query
        3. Prepends relevant memories section
        4. Truncates conversation history to fit within ~8000 token budget
        5. Returns list of Message objects ready for the provider

        Args:
            messages: Existing conversation history (user/assistant turns).
            query: The new user query to respond to.

        Returns:
            List of Message objects: [system, ...history, user_query]
        """
        # Build system prompt
        system_prompt = await self.build_system_prompt()

        # Search memory for relevant context
        relevant_memories = await self._memory.search(query, limit=5)

        # Build memory preamble if we found relevant memories
        memory_section = ""
        if relevant_memories:
            lines = ["Relevant memories:"]
            for mem in relevant_memories:
                lines.append(f"- [{mem.category}] {mem.content}")
            memory_section = "\n".join(lines)

        # Start building the output message list
        result: list[Message] = [Message(role="system", content=system_prompt)]

        # Calculate token budget for conversation history
        system_chars = len(system_prompt) + len(memory_section)
        query_chars = len(query)
        remaining_chars = _MAX_CONTEXT_CHARS - system_chars - query_chars

        # Truncate history from the oldest to fit budget
        history_messages: list[Message] = []
        total_chars = 0
        for msg in reversed(messages):
            msg_chars = len(msg.content)
            if total_chars + msg_chars > remaining_chars:
                break
            history_messages.insert(0, msg)
            total_chars += msg_chars

        # Add memory context as a system message if present
        if memory_section:
            result.append(Message(role="system", content=memory_section))

        # Add truncated history
        result.extend(history_messages)

        # Add the new user query
        result.append(Message(role="user", content=query))

        return result
