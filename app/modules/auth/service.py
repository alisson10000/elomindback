from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.modules.users.service import get_user_by_email, create_user

def signup(db: Session, *, email: str, name: str, role: str, password: str) -> str:
    if get_user_by_email(db, email=email):
        raise HTTPException(status_code=400, detail="Email already registered")

    # Validação mínima (MVP)
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 chars")

    user = create_user(
        db,
        email=email,
        name=name,
        role=role,
        password_hash=hash_password(password),
    )
    return create_access_token(subject=user.email)

def login(db: Session, *, email: str, password: str) -> str:
    user = get_user_by_email(db, email=email)
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return create_access_token(subject=user.email)
