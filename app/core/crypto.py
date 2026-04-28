from __future__ import annotations

import re
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.config import FIELD_ENCRYPTION_KEY

_FERNET_PREFIX = "gAAAA"
_URLSAFE_BASE64_RE = re.compile(r"^[A-Za-z0-9_-]+={0,2}$")


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet | None:
    if not FIELD_ENCRYPTION_KEY:
        return None
    return Fernet(FIELD_ENCRYPTION_KEY.encode("utf-8"))


def _require_fernet() -> Fernet:
    fernet = _get_fernet()
    if fernet is None:
        raise RuntimeError("FIELD_ENCRYPTION_KEY is not configured")
    return fernet


def is_encrypted(value: str | None) -> bool:
    if not value or not isinstance(value, str):
        return False

    text = value.strip()
    if not text.startswith(_FERNET_PREFIX):
        return False

    if not _URLSAFE_BASE64_RE.fullmatch(text):
        return False

    fernet = _get_fernet()
    if fernet is None:
        return True

    try:
        fernet.decrypt(text.encode("utf-8"))
        return True
    except InvalidToken:
        return False


def encrypt_text(value: str | None) -> str | None:
    if value is None:
        return None
    if is_encrypted(value):
        return value

    token = _require_fernet().encrypt(value.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_text(value: str | None) -> str | None:
    if value is None:
        return None
    if not is_encrypted(value):
        return value

    plain = _require_fernet().decrypt(value.encode("utf-8"))
    return plain.decode("utf-8")
