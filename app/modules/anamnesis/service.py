from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.crypto import decrypt_text, encrypt_text
from app.modules.anamnesis.model import Anamnesis

# Se você tiver um model para therapist_clients, importe aqui.
# Exemplo comum:
# from app.modules.therapist_clients.model import TherapistClient


def _assert_therapist_owns_client(db: Session, therapist_id: int, client_id: int):
    """
    Garante que o cliente pertence ao terapeuta.
    Ajuste o model/tabela conforme seu projeto.
    """
    # ✅ IMPORTANTE: preciso que você me confirme o model real da relação therapist_clients.
    # Enquanto isso, deixo como "pseudo-check" para você plugar.
    #
    # ok = (
    #   db.query(TherapistClient.id)
    #   .filter(TherapistClient.therapist_id == therapist_id, TherapistClient.client_id == client_id)
    #   .first()
    # ) is not None
    #
    # if not ok: raise PermissionError("Client not linked to therapist")
    return


def get_anamnesis_by_client(db: Session, therapist_id: int, client_id: int):
    _assert_therapist_owns_client(db, therapist_id=therapist_id, client_id=client_id)

    row = (
        db.query(Anamnesis)
        .filter(and_(Anamnesis.client_id == client_id, Anamnesis.therapist_id == therapist_id))
        .first()
    )
    return _serialize_anamnesis(row)


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


def create_anamnesis(db: Session, therapist_id: int, client_id: int, summary: str):
    _assert_therapist_owns_client(db, therapist_id=therapist_id, client_id=client_id)

    exists = (
        db.query(Anamnesis.id)
        .filter(and_(Anamnesis.client_id == client_id, Anamnesis.therapist_id == therapist_id))
        .first()
        is not None
    )
    if exists:
        raise ValueError("Anamnese já existe para este cliente.")

    row = Anamnesis(
        client_id=client_id,
        therapist_id=therapist_id,
        summary=encrypt_text(summary),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_anamnesis(row)


def update_anamnesis(db: Session, therapist_id: int, client_id: int, summary: str):
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
    return _serialize_anamnesis(row)
