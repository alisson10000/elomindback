from __future__ import annotations

import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.config import FIELD_ENCRYPTION_KEY


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def hash_email(email: str) -> str:
    normalized = normalize_email(email)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def _get_fernet_candidates() -> tuple[Fernet, ...]:
    if not FIELD_ENCRYPTION_KEY:
        raise RuntimeError("FIELD_ENCRYPTION_KEY is not configured")

    # Prepared for key rotation by returning a sequence of valid keys.
    return (Fernet(FIELD_ENCRYPTION_KEY.encode("utf-8")),)


def encrypt_value(value: str) -> str:
    if value is None:
        raise ValueError("Cannot encrypt None")

    return _get_fernet_candidates()[0].encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(value: str) -> str:
    if value is None:
        raise ValueError("Cannot decrypt None")

    payload = value.encode("utf-8")
    for fernet in _get_fernet_candidates():
        try:
            return fernet.decrypt(payload).decode("utf-8")
        except InvalidToken:
            continue

    raise ValueError("Unable to decrypt value with configured key(s)")


def mask_email(email: str) -> str:
    normalized = normalize_email(email)
    if "@" not in normalized:
        return "***"

    local_part, domain = normalized.split("@", 1)
    if not local_part:
        return f"***@{domain}"

    return f"{local_part[0]}***@{domain}"
