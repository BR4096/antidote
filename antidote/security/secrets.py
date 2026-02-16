"""Encrypted secret store using Fernet symmetric encryption.

Secrets are stored in ~/.antidote/.secrets as JSON with Fernet-encrypted values.
The encryption key is derived from the macOS hardware UUID via PBKDF2, making
the secrets file useless if copied to another machine.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


SECRETS_PATH = os.path.expanduser("~/.antidote/.secrets")
SALT = b"antidote-secret-store-v1"  # Fixed salt; security comes from hardware UUID


def _get_hardware_uuid() -> str | None:
    """Get macOS hardware UUID from ioreg."""
    try:
        result = subprocess.run(
            ["ioreg", "-d2", "-c", "IOPlatformExpertDevice"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.splitlines():
            if "IOPlatformUUID" in line:
                # Line looks like: "IOPlatformUUID" = "XXXXXXXX-XXXX-..."
                parts = line.split('"')
                for i, part in enumerate(parts):
                    if part == "IOPlatformUUID" and i + 2 < len(parts):
                        return parts[i + 2]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def _get_stored_password() -> str:
    """Get or create a stored password as fallback when hardware UUID is unavailable."""
    password_path = os.path.expanduser("~/.antidote/.keyfile")
    if os.path.exists(password_path):
        with open(password_path, "r") as f:
            return f.read().strip()
    # Generate a random password and store it
    password = base64.urlsafe_b64encode(os.urandom(32)).decode()
    os.makedirs(os.path.dirname(password_path), exist_ok=True)
    fd = os.open(password_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(password)
    return password


def _derive_key() -> bytes:
    """Derive a Fernet key from the machine identity."""
    hw_uuid = _get_hardware_uuid()
    if hw_uuid:
        key_material = hw_uuid
    else:
        key_material = _get_stored_password()

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=480_000,
    )
    derived = kdf.derive(key_material.encode())
    return base64.urlsafe_b64encode(derived)


class SecretStore:
    """Encrypted secret store backed by a local JSON file."""

    def __init__(self, path: str | None = None):
        self._path = path or SECRETS_PATH
        self._fernet = Fernet(_derive_key())

    def _load(self) -> dict[str, str]:
        """Load the raw encrypted secrets from disk."""
        if not os.path.exists(self._path):
            return {}
        with open(self._path, "r") as f:
            return json.load(f)

    def _save(self, data: dict[str, str]) -> None:
        """Write encrypted secrets to disk."""
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        fd = os.open(self._path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)

    def save_secret(self, name: str, value: str) -> None:
        """Encrypt and store a secret."""
        data = self._load()
        encrypted = self._fernet.encrypt(value.encode()).decode()
        data[name] = encrypted
        self._save(data)

    def get_secret(self, name: str) -> str | None:
        """Decrypt and return a secret, or None if not found."""
        data = self._load()
        encrypted = data.get(name)
        if encrypted is None:
            return None
        try:
            return self._fernet.decrypt(encrypted.encode()).decode()
        except InvalidToken:
            return None

    def list_secrets(self) -> list[str]:
        """Return secret names (not values)."""
        return list(self._load().keys())

    def delete_secret(self, name: str) -> bool:
        """Remove a secret. Returns True if it existed."""
        data = self._load()
        if name not in data:
            return False
        del data[name]
        self._save(data)
        return True
