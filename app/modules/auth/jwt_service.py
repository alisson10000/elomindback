from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.auth.model import RevokedToken


def revoke_token(
    db: Session,
    token_jti: str,
    user_id: int | None = None,
    expires_at: datetime | None = None,
) -> bool:
    """
    Revoga um token por `jti` sem nunca persistir o JWT completo.
    Retorna True se criou um novo registro; False se já existia.
    """
    token_jti = (token_jti or "").strip()
    if not token_jti:
        return False

    existing = db.execute(
        select(RevokedToken.id).where(RevokedToken.token_jti == token_jti).limit(1)
    ).first()
    if existing:
        return False

    row = RevokedToken(
        token_jti=token_jti,
        user_id=user_id,
        expires_at=expires_at,
    )
    db.add(row)
    db.commit()
    return True


def is_token_revoked(db: Session, token_jti: str) -> bool:
    token_jti = (token_jti or "").strip()
    if not token_jti:
        return False

    exists = db.execute(
        select(RevokedToken.id).where(RevokedToken.token_jti == token_jti).limit(1)
    ).first()
    return bool(exists)


def delete_expired_revoked_tokens(db: Session, *, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    # Usamos timestamp timezone-aware, mas o backend pode armazenar sem tz;
    # manter comparação simples e compatível com SQLite/MySQL.
    now_naive = now.replace(tzinfo=None)

    result = db.execute(
        delete(RevokedToken).where(
            RevokedToken.expires_at.is_not(None),
            RevokedToken.expires_at <= now_naive,
        )
    )
    db.commit()
    return int(getattr(result, "rowcount", 0) or 0)


def jti_prefix(jti: str | None, *, keep: int = 8) -> str | None:
    value = (jti or "").strip()
    if not value:
        return None
    return value[:keep]


def exp_to_datetime_utc(exp: Any) -> datetime | None:
    try:
        exp_int = int(exp)
    except Exception:
        return None
    return datetime.fromtimestamp(exp_int, tz=timezone.utc)

