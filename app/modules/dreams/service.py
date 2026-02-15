from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.dreams.model import Dream
from app.modules.therapist_clients.model import TherapistClient


# ======================
# Helpers
# ======================
def _get_therapist_id_for_client(db: Session, *, client_id: int) -> int:
    """
    Pega o therapist_id vinculado a esse client_id.
    Se não existir vínculo, o cliente não pode registrar sonho (regra de negócio).
    """
    link = (
        db.query(TherapistClient)
        .filter(TherapistClient.client_id == client_id)
        .order_by(TherapistClient.id.desc())
        .first()
    )
    if not link:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client has no therapist assigned",
        )
    return link.therapist_id


def _ensure_therapist_owns_client(db: Session, *, therapist_id: int, client_id: int) -> None:
    """
    Garante que o terapeuta tem vínculo com o cliente.
    """
    link = (
        db.query(TherapistClient)
        .filter(
            TherapistClient.therapist_id == therapist_id,
            TherapistClient.client_id == client_id,
        )
        .one_or_none()
    )
    if not link:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )


def _get_dream_or_404(db: Session, *, dream_id: int) -> Dream:
    d = db.query(Dream).filter(Dream.id == dream_id).one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="Dream not found")
    return d


# ======================
# CLIENT
# ======================
def create_dream(db: Session, *, client_id: int, description: str) -> Dream:
    therapist_id = _get_therapist_id_for_client(db, client_id=client_id)

    text = (description or "").strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Description is required",
        )

    dream = Dream(
        client_id=client_id,
        therapist_id=therapist_id,
        description=text,
    )
    db.add(dream)
    db.commit()
    db.refresh(dream)
    return dream


# ======================
# THERAPIST
# ======================
def list_dreams_by_client(db: Session, *, therapist_id: int, client_id: int) -> list[Dream]:
    _ensure_therapist_owns_client(db, therapist_id=therapist_id, client_id=client_id)

    return (
        db.query(Dream)
        .filter(Dream.client_id == client_id, Dream.therapist_id == therapist_id)
        .order_by(Dream.id.desc())
        .all()
    )


def update_dream_as_therapist(
    db: Session,
    *,
    therapist_id: int,
    dream_id: int,
    update_data,
) -> Dream:
    dream = _get_dream_or_404(db, dream_id=dream_id)

    # protege: só o terapeuta dono pode editar
    if dream.therapist_id != therapist_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if getattr(update_data, "therapist_tags", None) is not None:
        dream.therapist_tags = update_data.therapist_tags

    if getattr(update_data, "therapist_notes", None) is not None:
        dream.therapist_notes = update_data.therapist_notes

    db.commit()
    db.refresh(dream)
    return dream
