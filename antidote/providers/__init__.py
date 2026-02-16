"""Provider factory and exports.

Usage:
    from antidote.providers import get_provider
    provider = get_provider()          # default from config
    provider = get_provider("ollama")  # specific provider
"""

from __future__ import annotations

from antidote.providers.base import BaseProvider, LLMResponse, Message, ToolDefinition


def get_provider(name: str | None = None) -> BaseProvider:
    """Get a provider by name. Defaults to the config default."""
    from antidote.config import Config

    name = name or Config().providers.default
    if name == "openrouter":
        from antidote.providers.openrouter import OpenRouterProvider

        return OpenRouterProvider()
    elif name == "ollama":
        from antidote.providers.ollama import OllamaProvider

        return OllamaProvider()
    else:
        raise ValueError(f"Unknown provider: {name}")


__all__ = [
    "BaseProvider",
    "LLMResponse",
    "Message",
    "ToolDefinition",
    "get_provider",
]
