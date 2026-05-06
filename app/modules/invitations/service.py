from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.invite_tokens import generate_invite_token, hash_invite_token
from app.core.security import hash_password
from app.modules.audit.service import log_action
from app.modules.invitations.model import Invitation
from app.modules.therapist_clients.service import link_therapist_client
from app.modules.users.model import User
from app.modules.users.service import create_user, get_user_by_email
from utils.security import normalize_email

INVITE_TTL_DAYS = 3


def _now_utc() -> datetime:
    return datetime.utcnow()


def get_active_invitation_by_email(db: Session, *, therapist_id: int, email: str) -> Invitation | None:
    now = _now_utc()
    return (
        db.query(Invitation)
        .filter(
            Invitation.therapist_id == therapist_id,
            Invitation.email == normalize_email(email),
            Invitation.used_at.is_(None),
            Invitation.expires_at > now,
        )
        .order_by(Invitation.id.desc())
        .first()
    )


def create_invitation(
    db: Session,
    *,
    therapist_id: int,
    email: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[Invitation, str]:
    normalized_email = normalize_email(email)

    if get_user_by_email(db, email=normalized_email):
        raise ValueError("Email already registered")

    active = get_active_invitation_by_email(db, therapist_id=therapist_id, email=normalized_email)
    if active:
        active.used_at = _now_utc()
        db.commit()
        db.refresh(active)

    token = generate_invite_token()
    token_h = hash_invite_token(token)

    inv = Invitation(
        therapist_id=therapist_id,
        email=normalized_email,
        token_hash=token_h,
        expires_at=_now_utc() + timedelta(days=INVITE_TTL_DAYS),
        used_at=None,
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    log_action(
        db,
        user_id=therapist_id,
        action="INVITATION_CREATED",
        resource_type="invitation",
        resource_id=inv.id,
        ip_address=ip_address,
        user_agent=user_agent,
        details={"therapist_id": therapist_id, "email": normalized_email},
    )
    return inv, token


def get_invitation_by_token(db: Session, *, token: str) -> Invitation | None:
    token_h = hash_invite_token(token)
    return db.query(Invitation).filter(Invitation.token_hash == token_h).first()


def validate_invitation(db: Session, *, token: str) -> Invitation | None:
    inv = get_invitation_by_token(db, token=token)
    if not inv:
        return None
    if inv.used_at is not None:
        return None
    if inv.expires_at < _now_utc():
        return None
    return inv


def signup_from_invitation(
    db: Session,
    *,
    token: str,
    name: str,
    password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> User | None:
    inv = validate_invitation(db, token=token)
    if not inv:
        return None

    email = normalize_email(inv.email)

    if get_user_by_email(db, email=email):
        return None

    user = create_user(
        db,
        email=email,
        name=name,
        role="client",
        password_hash=hash_password(password),
    )

    link_therapist_client(db, therapist_id=inv.therapist_id, client_id=user.id)

    inv.used_at = _now_utc()
    db.commit()
    db.refresh(inv)
    log_action(
        db,
        user_id=user.id,
        action="INVITATION_USED",
        resource_type="invitation",
        resource_id=inv.id,
        ip_address=ip_address,
        user_agent=user_agent,
        details={"therapist_id": inv.therapist_id, "client_id": user.id, "email": email, "name": name},
    )

    return user
