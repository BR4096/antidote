"""Provider interface and data types for LLM communication.

All LLM providers (OpenRouter, Ollama, etc.) implement BaseProvider.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Message:
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: list | None = None
    tool_call_id: str | None = None


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict  # JSON Schema


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list | None  # List of {id, name, arguments}
    usage: dict | None  # {prompt_tokens, completion_tokens}


class BaseProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Send messages to LLM, get response. Supports tool calling."""
        ...
