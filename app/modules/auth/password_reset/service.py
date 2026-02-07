from datetime import datetime, timedelta, timezone
import secrets
import hashlib

from sqlalchemy.orm import Session

from app.modules.users.model import User
from app.modules.auth.password_reset.model import PasswordResetToken
from app.core.security import hash_password


RESET_TOKEN_EXPIRE_MINUTES = 30


def _now_utc() -> datetime:
    """UTC timezone-aware now."""
    return datetime.now(timezone.utc)


def _as_utc_aware(dt: datetime | None) -> datetime | None:
    """
    Normaliza datetime para UTC timezone-aware.
    No MySQL, DATETIME costuma voltar naive (tzinfo=None).
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # assume que o valor vindo do banco já representa UTC
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _hash_token(token_plain: str) -> str:
    return hashlib.sha256(token_plain.encode()).hexdigest()


def create_password_reset(db: Session, email: str):
    """
    Cria um token de reset e retorna (token_plain, user).
    Se o usuário não existir, retorna None.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None

    # ✅ você pode trocar por código de 6 dígitos se quiser, mas mantém token longo por enquanto
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
    """
    Confirma o reset usando email + token + nova senha (fluxo 100% dentro do app).
    Valida:
    - usuário existe (retorna erro genérico se não)
    - token existe para aquele usuário
    - não foi usado
    - não expirou
    Atualiza:
    - senha do usuário (hash)
    - marca token como usado
    - seta used_at
    """
    # 1) achar usuário
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # genérico pra não vazar se email existe
        raise ValueError("Invalid token")

    # 2) achar token do usuário
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

    # 3) validações
    if bool(reset.used):
        raise ValueError("Token already used")

    now = _now_utc()
    expires_at = _as_utc_aware(reset.expires_at)

    if expires_at is None or expires_at < now:
        raise ValueError("Token expired")

    # 4) atualizar senha + marcar usado
    user.password_hash = hash_password(new_password)

    reset.used = True
    reset.used_at = now

    db.commit()
    return True
