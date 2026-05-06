from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.modules.audit.service import log_action
from app.modules.users.service import create_user, get_user_by_email
from utils.security import normalize_email


VALID_ROLES = {"client", "therapist"}


def signup(db: Session, *, email: str, name: str, role: str, password: str) -> str:
    email = normalize_email(email)
    name = (name or "").strip()
    role = (role or "").strip().lower()

    if not email or not name or not password:
        raise HTTPException(status_code=400, detail="Dados invÃƒÂ¡lidos")

    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Role invÃƒÂ¡lida (use client ou therapist)")

    existing = get_user_by_email(db, email=email)
    if existing:
        raise HTTPException(status_code=400, detail="Email jÃƒÂ¡ cadastrado")

    user = create_user(
        db,
        email=email,
        name=name,
        role=role,
        password_hash=hash_password(password),
    )

    return create_access_token(subject=str(user.id))


def login(
    db: Session,
    *,
    email: str,
    password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> str:
    email = normalize_email(email)

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email e senha sÃƒÂ£o obrigatÃƒÂ³rios",
        )

    user = get_user_by_email(db, email=email)

    if not user or not verify_password(password, user.password_hash):
        log_action(
            db,
            action="LOGIN_FAILED",
            resource_type="auth",
            ip_address=ip_address,
            user_agent=user_agent,
            details={"email": email, "reason": "invalid_credentials"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais invÃƒÂ¡lidas",
        )

    if not getattr(user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User inactive",
        )

    token = create_access_token(subject=str(user.id))
    log_action(
        db,
        user_id=user.id,
        action="LOGIN_SUCCESS",
        resource_type="auth",
        resource_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
        details={"role": user.role},
    )
    return token
