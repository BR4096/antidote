"""Configuration loader for Antidote.

Loads from ~/.antidote/config.json, merges with defaults, expands ~ in paths,
and reads secrets from the encrypted store (falling back to env vars).

Usage:
    from antidote.config import Config
    config = Config()
    print(config.providers["default"])
"""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv

# Load .env if it exists (before anything else reads env vars)
load_dotenv(os.path.expanduser("~/.antidote/.env"))

CONFIG_PATH = os.path.expanduser("~/.antidote/config.json")

DEFAULTS: dict[str, Any] = {
    "name": "Antidote",
    "version": "0.1.0",
    "providers": {
        "default": "openrouter",
        "openrouter": {
            "model": "anthropic/claude-sonnet-4-20250514",
        },
        "ollama": {
            "model": "llama3.2",
            "base_url": "http://localhost:11434",
        },
    },
    "channels": {
        "telegram": {
            "enabled": True,
        },
    },
    "memory": {
        "db_path": "~/.antidote/memory.db",
        "max_context_memories": 10,
    },
    "workspace": "~/.antidote/workspace",
    "routing": {
        "enabled": True,
        "fast_model": "anthropic/claude-haiku-4.5",
        "full_model": None,  # None = use provider default (Sonnet 4)
    },
    "identity": {
        "soul": "workspace/SOUL.md",
        "agents": "workspace/AGENTS.md",
        "user": "workspace/USER.md",
    },
    "safety": {
        "blocked_commands": [
            "rm -rf /",
            "mkfs",
            "dd if=",
            "shutdown",
            "reboot",
            "> /dev/sd",
        ],
        "max_command_timeout": 60,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base. Override wins for leaf values."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _expand_paths(obj: Any) -> Any:
    """Recursively expand ~ in string values that look like paths."""
    if isinstance(obj, str) and "~" in obj:
        return os.path.expanduser(obj)
    if isinstance(obj, dict):
        return {k: _expand_paths(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_expand_paths(item) for item in obj]
    return obj


class _ConfigData:
    """Dot-access wrapper over a nested dict."""

    def __init__(self, data: dict[str, Any]):
        object.__setattr__(self, "_data", data)

    def __getattr__(self, name: str) -> Any:
        try:
            data = object.__getattribute__(self, "_data")
            value = data[name]
        except KeyError:
            raise AttributeError(
                f"Config has no attribute '{name}'"
            ) from None
        if isinstance(value, dict):
            return _ConfigData(value)
        return value

    def __getitem__(self, key: str) -> Any:
        value = self._data[key]
        if isinstance(value, dict):
            return _ConfigData(value)
        return value

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def get(self, key: str, default: Any = None) -> Any:
        value = self._data.get(key, default)
        if isinstance(value, dict):
            return _ConfigData(value)
        return value

    def to_dict(self) -> dict[str, Any]:
        return self._data

    def __repr__(self) -> str:
        return f"ConfigData({self._data!r})"


class Config(_ConfigData):
    """Singleton configuration object for Antidote.

    Loads config.json, merges with defaults, expands paths, and
    provides access to encrypted secrets.
    """

    _instance: Config | None = None

    def __new__(cls, path: str | None = None) -> Config:
        if cls._instance is not None:
            return cls._instance
        instance = super().__new__(cls)
        cls._instance = instance
        return instance

    def __init__(self, path: str | None = None):
        # Skip re-init if singleton already set up
        try:
            object.__getattribute__(self, "_data")
            return
        except AttributeError:
            pass

        config_path = path or CONFIG_PATH
        raw: dict[str, Any] = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                raw = json.load(f)

        merged = _deep_merge(DEFAULTS, raw)
        expanded = _expand_paths(merged)
        self._validate(expanded)
        super().__init__(expanded)

        # Lazily loaded secrets store (avoid circular import at module level)
        object.__setattr__(self, "_secrets_store", None)

    @staticmethod
    def _validate(data: dict[str, Any]) -> None:
        """Validate that required top-level fields exist."""
        required = ["providers", "channels", "memory", "workspace", "safety"]
        for field in required:
            if field not in data:
                raise ValueError(f"Missing required config field: '{field}'")

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (useful for testing)."""
        cls._instance = None

    def _get_secrets_store(self):
        """Lazily import and instantiate the SecretStore."""
        store = object.__getattribute__(self, "_secrets_store")
        if store is None:
            from antidote.security.secrets import SecretStore
            store = SecretStore()
            object.__setattr__(self, "_secrets_store", store)
        return store

    def get_secret(self, name: str) -> str | None:
        """Retrieve a secret from the encrypted store, falling back to env var.

        Lookup order:
            1. Encrypted secret store (~/.antidote/.secrets)
            2. Environment variable with the same name
        """
        store = self._get_secrets_store()
        value = store.get_secret(name)
        if value is not None:
            return value
        return os.environ.get(name)
