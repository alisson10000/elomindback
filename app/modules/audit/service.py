from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session, sessionmaker

from app.modules.audit.model import AuditLog

SENSITIVE_DETAIL_KEYS = {
    "access_token",
    "anamnesis",
    "clinical_notes",
    "content",
    "dream",
    "email",
    "name",
    "password",
    "reflection",
    "refresh_token",
    "token",
}

EMAIL_PATTERN = re.compile(r"([A-Za-z0-9._%+\-]+)@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})")
BEARER_PATTERN = re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b", re.IGNORECASE)
JWT_PATTERN = re.compile(r"\beyJ[A-Za-z0-9_\-]+(?:\.[A-Za-z0-9_\-]+){1,2}\b")


def get_client_ip(request: Request | None) -> str | None:
    if request is None:
        return None

    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first_ip = forwarded_for.split(",")[0].strip()
        if first_ip:
            return first_ip[:64]

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()[:64]

    client = getattr(request, "client", None)
    host = getattr(client, "host", None)
    return host[:64] if host else None


def get_user_agent(request: Request | None) -> str | None:
    if request is None:
        return None
    user_agent = request.headers.get("user-agent")
    if not user_agent:
        return None
    return user_agent[:512]


def sanitize_audit_details(details: Any) -> Any:
    return _sanitize_value(details)


def log_action(
    db: Session,
    user_id: int | None = None,
    action: str = "",
    resource_type: str | None = None,
    resource_id: int | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    details: Any = None,
) -> None:
    if not action:
        return

    sanitized_details = sanitize_audit_details(details)

    try:
        audit_session = _build_audit_session(db)
    except Exception:
        return

    try:
        _persist_audit_log(
            audit_session,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address or None,
            user_agent=user_agent or None,
            details=_serialize_details(sanitized_details),
        )
    except Exception:
        try:
            audit_session.rollback()
        except Exception:
            pass
    finally:
        audit_session.close()


def _build_audit_session(db: Session) -> Session:
    bind = db.get_bind()
    factory = sessionmaker(bind=bind, autoflush=False, autocommit=False, expire_on_commit=False)
    return factory()


def _persist_audit_log(
    audit_session: Session,
    *,
    user_id: int | None,
    action: str,
    resource_type: str | None,
    resource_id: int | None,
    ip_address: str | None,
    user_agent: str | None,
    details: str | None,
) -> None:
    row = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address[:64] if ip_address else None,
        user_agent=user_agent[:512] if user_agent else None,
        details=details,
    )
    audit_session.add(row)
    audit_session.commit()


def _serialize_details(details: Any) -> str | None:
    if details is None:
        return None
    return json.dumps(details, ensure_ascii=False, sort_keys=True)


def _sanitize_value(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, nested_value in value.items():
            normalized_key = str(key).strip().lower()
            if normalized_key in SENSITIVE_DETAIL_KEYS:
                sanitized[str(key)] = "[REDACTED]"
            else:
                sanitized[str(key)] = _sanitize_value(nested_value)
        return sanitized

    if isinstance(value, (list, tuple, set)):
        return [_sanitize_value(item) for item in value]

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (bool, int, float)):
        return value

    return _sanitize_string(str(value))


def _sanitize_string(value: str) -> str:
    if not value:
        return value

    sanitized = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", value)
    sanitized = BEARER_PATTERN.sub("[REDACTED_TOKEN]", sanitized)
    sanitized = JWT_PATTERN.sub("[REDACTED_TOKEN]", sanitized)
    return sanitized
