from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.modules.users.service import create_user, get_user_by_email
from utils.security import normalize_email


VALID_ROLES = {"client", "therapist"}


def signup(db: Session, *, email: str, name: str, role: str, password: str) -> str:
    email = normalize_email(email)
    name = (name or "").strip()
    role = (role or "").strip().lower()

    if not email or not name or not password:
        raise HTTPException(status_code=400, detail="Dados invÃ¡lidos")

    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Role invÃ¡lida (use client ou therapist)")

    existing = get_user_by_email(db, email=email)
    if existing:
        raise HTTPException(status_code=400, detail="Email jÃ¡ cadastrado")

    user = create_user(
        db,
        email=email,
        name=name,
        role=role,
        password_hash=hash_password(password),
    )

    return create_access_token(subject=str(user.id))


def login(db: Session, *, email: str, password: str) -> str:
    email = normalize_email(email)

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email e senha sÃ£o obrigatÃ³rios",
        )

    user = get_user_by_email(db, email=email)

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais invÃ¡lidas",
        )

    if not getattr(user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User inactive",
        )

    return create_access_token(subject=str(user.id))
