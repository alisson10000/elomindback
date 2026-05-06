from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_text, encrypt_text
from app.modules.anamnesis.model import Anamnesis
from app.modules.audit.service import log_action


def _assert_therapist_owns_client(db: Session, therapist_id: int, client_id: int):
    return


def get_anamnesis_by_client(
    db: Session,
    therapist_id: int,
    client_id: int,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
):
    _assert_therapist_owns_client(db, therapist_id=therapist_id, client_id=client_id)

    row = (
        db.query(Anamnesis)
        .filter(and_(Anamnesis.client_id == client_id, Anamnesis.therapist_id == therapist_id))
        .first()
    )
    serialized = _serialize_anamnesis(row)
    if serialized:
        log_action(
            db,
            user_id=therapist_id,
            action="ANAMNESIS_VIEWED",
            resource_type="anamnesis",
            resource_id=serialized["id"],
            ip_address=ip_address,
            user_agent=user_agent,
            details={"client_id": client_id, "therapist_id": therapist_id},
        )
    return serialized


def _serialize_anamnesis(row: Anamnesis | None):
    if not row:
        return None

    return {
        "id": row.id,
        "client_id": row.client_id,
        "therapist_id": row.therapist_id,
        "summary": decrypt_text(row.summary),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def create_anamnesis(
    db: Session,
    therapist_id: int,
    client_id: int,
    summary: str,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
):
    _assert_therapist_owns_client(db, therapist_id=therapist_id, client_id=client_id)

    exists = (
        db.query(Anamnesis.id)
        .filter(and_(Anamnesis.client_id == client_id, Anamnesis.therapist_id == therapist_id))
        .first()
        is not None
    )
    if exists:
        raise ValueError("Anamnese jÃ¡ existe para este cliente.")

    row = Anamnesis(
        client_id=client_id,
        therapist_id=therapist_id,
        summary=encrypt_text(summary),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    log_action(
        db,
        user_id=therapist_id,
        action="ANAMNESIS_CREATED",
        resource_type="anamnesis",
        resource_id=row.id,
        ip_address=ip_address,
        user_agent=user_agent,
        details={"client_id": client_id, "therapist_id": therapist_id},
    )
    return _serialize_anamnesis(row)


def update_anamnesis(
    db: Session,
    therapist_id: int,
    client_id: int,
    summary: str,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
):
    _assert_therapist_owns_client(db, therapist_id=therapist_id, client_id=client_id)

    row = (
        db.query(Anamnesis)
        .filter(and_(Anamnesis.client_id == client_id, Anamnesis.therapist_id == therapist_id))
        .first()
    )
    if not row:
        return None

    row.summary = encrypt_text(summary)
    db.commit()
    db.refresh(row)
    log_action(
        db,
        user_id=therapist_id,
        action="ANAMNESIS_UPDATED",
        resource_type="anamnesis",
        resource_id=row.id,
        ip_address=ip_address,
        user_agent=user_agent,
        details={"client_id": client_id, "therapist_id": therapist_id},
    )
    return _serialize_anamnesis(row)
