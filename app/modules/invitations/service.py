from __future__ import annotations

from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.modules.invitations.model import Invitation
from app.modules.users.model import User
from app.modules.users.service import get_user_by_email, create_user
from app.modules.therapist_clients.service import link_therapist_client

from app.core.security import hash_password
from app.core.invite_tokens import generate_invite_token, hash_invite_token
from utils.security import normalize_email

INVITE_TTL_DAYS = 3


def _now_utc() -> datetime:
    # seu projeto está usando datetime.utcnow(), então mantive o mesmo padrão
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
) -> tuple[Invitation, str]:
    """
    Cria um convite e retorna (invitation, token_puro).

    Regras MVP:
    - Se o e-mail já for usuário cadastrado -> não cria convite
    - Se já existir convite ativo (não usado e não expirado) -> cria um novo token (reenvio) OU retorna erro
      (aqui eu escolhi REGERAR um novo convite para simplificar reenvio)
    """
    normalized_email = normalize_email(email)

    # 1) Se já existe usuário com esse email, não faz sentido convidar
    if get_user_by_email(db, email=normalized_email):
        raise ValueError("Email already registered")

    # 2) Se já existe convite ativo, invalida o anterior e gera outro (reenvio simples)
    active = get_active_invitation_by_email(db, therapist_id=therapist_id, email=normalized_email)
    if active:
        active.used_at = _now_utc()  # marca como "não mais válido" (não é usado, mas encerra)
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
) -> User | None:
    """
    Usa um convite válido para criar um usuário cliente e vincular ao terapeuta.
    """
    inv = validate_invitation(db, token=token)
    if not inv:
        return None

    email = normalize_email(inv.email)

    # Se já existe usuário com esse email, bloqueia
    if get_user_by_email(db, email=email):
        return None

    # cria usuário cliente
    user = create_user(
        db,
        email=email,
        name=name,
        role="client",
        password_hash=hash_password(password),
    )

    # vincula terapeuta -> cliente
    link_therapist_client(db, therapist_id=inv.therapist_id, client_id=user.id)

    # marca convite como usado (agora sim, usado de verdade)
    inv.used_at = _now_utc()
    db.commit()
    db.refresh(inv)

    return user
