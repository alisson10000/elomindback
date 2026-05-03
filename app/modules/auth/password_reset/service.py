from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.auth.password_reset.model import PasswordResetToken
from app.modules.users.service import get_user_by_email
from utils.security import normalize_email


RESET_TOKEN_EXPIRE_MINUTES = 30


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _hash_token(token_plain: str) -> str:
    return hashlib.sha256(token_plain.encode()).hexdigest()


def create_password_reset(db: Session, email: str):
    user = get_user_by_email(db, email=normalize_email(email))
    if not user:
        return None

    token_plain = secrets.token_urlsafe(32)
    token_hash = _hash_token(token_plain)
    expires_at = _now_utc() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)

    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        used=False,
        used_at=None,
    )

    db.add(reset)
    db.commit()
    db.refresh(reset)

    return token_plain, user


def reset_password_with_token(db: Session, email: str, token: str, new_password: str):
    user = get_user_by_email(db, email=normalize_email(email))
    if not user:
        raise ValueError("Invalid token")

    token_hash = _hash_token(token)
    reset = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.token_hash == token_hash,
        )
        .first()
    )
    if not reset:
        raise ValueError("Invalid token")

    if bool(reset.used):
        raise ValueError("Token already used")

    now = _now_utc()
    expires_at = _as_utc_aware(reset.expires_at)

    if expires_at is None or expires_at < now:
        raise ValueError("Token expired")

    user.password_hash = hash_password(new_password)
    reset.used = True
    reset.used_at = now

    db.commit()
    return True
