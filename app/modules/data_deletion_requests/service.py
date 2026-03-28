# app/modules/data_deletion_requests/service.py
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.modules.data_deletion_requests.model import DataDeletionRequest
from app.modules.feedback.model import Feedback
from app.modules.reflections.model import Reflection
from app.modules.dreams.model import Dream
from app.modules.anamnesis.model import Anamnesis
from app.modules.consents.model import Consent
from app.modules.therapist_clients.model import TherapistClient
from app.modules.users.model import User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_pending_request(db: Session, *, client_id: int) -> DataDeletionRequest | None:
    return (
        db.query(DataDeletionRequest)
        .filter(
            DataDeletionRequest.client_id == client_id,
            DataDeletionRequest.status == "pending",
        )
        .order_by(DataDeletionRequest.id.desc())
        .first()
    )


# ======================
# Client-facing (MVP)
# ======================
def create_data_deletion_request(db: Session, *, client: User) -> DataDeletionRequest:
    pending = _get_pending_request(db, client_id=client.id)
    if pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="There is already a pending deletion request",
        )

    req = DataDeletionRequest(
        client_id=client.id,
        client_email=getattr(client, "email", None),
        client_name=getattr(client, "name", None),
        status="pending",
        requested_at=_utcnow(),
    )

    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def get_my_latest_deletion_request(db: Session, *, client_id: int) -> DataDeletionRequest | None:
    return (
        db.query(DataDeletionRequest)
        .filter(DataDeletionRequest.client_id == client_id)
        .order_by(DataDeletionRequest.id.desc())
        .first()
    )


# ======================
# Manual execution (MVP)
# ======================
def execute_full_deletion(db: Session, *, client_id: int) -> None:
    """
    Ordem segura (FK):
      Feedback -> Reflections -> Dreams -> Anamnesis -> Consents -> TherapistClient -> (Request) -> User

    Mantém audit do pedido se o banco permitir:
      - marca completed
      - tenta SET NULL no client_id do request (precisa client_id nullable + FK ON DELETE SET NULL)
    Se não permitir, faz fallback:
      - remove o request antes de deletar o user (pra não travar).
    """

    req = _get_pending_request(db, client_id=client_id)

    # 1) Feedback (subquery)
    reflection_ids_subq = select(Reflection.id).where(Reflection.client_id == client_id)
    db.execute(delete(Feedback).where(Feedback.reflection_id.in_(reflection_ids_subq)))

    # 2) Reflections
    db.execute(delete(Reflection).where(Reflection.client_id == client_id))

    # 3) Dreams
    db.execute(delete(Dream).where(Dream.client_id == client_id))

    # 4) Anamnesis
    db.execute(delete(Anamnesis).where(Anamnesis.client_id == client_id))

    # 5) Consents  ✅ (NO SEU BANCO É client_id, NÃO user_id)
    db.execute(delete(Consent).where(Consent.client_id == client_id))

    # 6) TherapistClient
    db.execute(delete(TherapistClient).where(TherapistClient.client_id == client_id))

    # 7) Request: marcar completed + tentar manter audit
    if req:
        req.status = "completed"
        req.completed_at = _utcnow()

        # tenta manter o audit após remover o user
        # (só funciona se client_id for NULLABLE e FK estiver ON DELETE SET NULL)
        try:
            req.client_id = None
            db.flush()
        except IntegrityError:
            db.rollback()
            # reabre transação e refaz deleções (rollback limpou as operações pendentes)
            # -> estratégia simples: executa tudo de novo mas sem tentar NULL
            # (MVP safe: remove request e segue)

            # refaz deleções (idempotente)
            reflection_ids_subq = select(Reflection.id).where(Reflection.client_id == client_id)
            db.execute(delete(Feedback).where(Feedback.reflection_id.in_(reflection_ids_subq)))
            db.execute(delete(Reflection).where(Reflection.client_id == client_id))
            db.execute(delete(Dream).where(Dream.client_id == client_id))
            db.execute(delete(Anamnesis).where(Anamnesis.client_id == client_id))
            db.execute(delete(Consent).where(Consent.client_id == client_id))
            db.execute(delete(TherapistClient).where(TherapistClient.client_id == client_id))

            # marca completed (sem NULL) e apaga o request depois
            req = _get_pending_request(db, client_id=client_id)
            if req:
                req.status = "completed"
                req.completed_at = _utcnow()
                db.flush()

            # remove requests do client antes de deletar user (para não travar FK)
            db.execute(delete(DataDeletionRequest).where(DataDeletionRequest.client_id == client_id))

    else:
        # sem request pendente, mas mesmo assim remove qualquer request do client (se existir)
        db.execute(delete(DataDeletionRequest).where(DataDeletionRequest.client_id == client_id))

    # 8) User
    db.execute(delete(User).where(User.id == client_id))

    db.commit()
