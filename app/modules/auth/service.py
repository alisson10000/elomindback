from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.modules.users.model import User
from app.core.security import hash_password, verify_password, create_access_token


VALID_ROLES = {"client", "therapist"}


def signup(db: Session, *, email: str, name: str, role: str, password: str) -> str:
    email = (email or "").strip().lower()
    name = (name or "").strip()
    role = (role or "").strip().lower()

    if not email or not name or not password:
        raise HTTPException(status_code=400, detail="Dados inválidos")

    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Role inválida (use client ou therapist)")

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    user = User(
        email=email,
        name=name,
        role=role,
        password_hash=hash_password(password),
    )

    # ✅ se seu model tiver is_active, garante ativo no cadastro
    if hasattr(user, "is_active"):
        user.is_active = True

    db.add(user)
    db.commit()
    db.refresh(user)

    return create_access_token(subject=user.email)


def login(db: Session, *, email: str, password: str) -> str:
    email = (email or "").strip().lower()

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email e senha são obrigatórios",
        )

    user = db.query(User).filter(User.email == email).first()

    # ✅ não revela se email existe ou não
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )

    # ✅ BLOQUEIA usuário desativado
    if not getattr(user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User inactive",
        )

    return create_access_token(subject=user.email)
