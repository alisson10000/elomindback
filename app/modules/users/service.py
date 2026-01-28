from sqlalchemy.orm import Session
from app.modules.users.model import User

def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, *, email: str, name: str, role: str, password_hash: str) -> User:
    user = User(email=email, name=name, role=role, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()

def list_clients(db: Session) -> list[User]:
    return (
        db.query(User)
        .filter(User.role == "client")
        .order_by(User.name.asc())
        .all()
    )

def set_user_active(db: Session, *, user: User, is_active: bool) -> User:
    user.is_active = bool(is_active)
    db.commit()
    db.refresh(user)
    return user
