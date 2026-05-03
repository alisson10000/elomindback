from sqlalchemy.orm import Session

from app.modules.users.model import User
from utils.security import encrypt_value, hash_email, normalize_email


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email_hash == hash_email(email)).first()


def create_user(db: Session, *, email: str, name: str, role: str, password_hash: str) -> User:
    normalized_email = normalize_email(email)
    clean_name = (name or "").strip()

    user = User(
        role=role,
        password_hash=password_hash,
        email_hash=hash_email(normalized_email),
        email_encrypted=encrypt_value(normalized_email),
        name_encrypted=encrypt_value(clean_name),
        legacy_email=None,
        legacy_name=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "is_active": getattr(user, "is_active", True),
    }


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def list_clients(db: Session) -> list[User]:
    clients = db.query(User).filter(User.role == "client").all()
    return sorted(clients, key=lambda user: (user.name or "").lower())


def set_user_active(db: Session, *, user: User, is_active: bool) -> User:
    user.is_active = bool(is_active)
    db.commit()
    db.refresh(user)
    return user
