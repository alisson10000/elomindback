# app/modules/data_deletion_requests/service.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, inspect, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.modules.audit.service import log_action
from app.modules.auth.password_reset.model import PasswordResetToken
from app.modules.data_deletion_requests.model import DataDeletionRequest
from app.modules.feedback.model import Feedback
from app.modules.reflections.model import Reflection
from app.modules.dreams.model import Dream
from app.modules.anamnesis.model import Anamnesis
from app.modules.consents.model import Consent
from app.modules.push_tokens.model import UserPushToken
from app.modules.therapist_clients.model import TherapistClient
from app.modules.users.model import User
from app.modules.users.service import serialize_user

DATA_DELETION_STATUS_PENDING = "pending"
DATA_DELETION_STATUS_PROCESSING = "processing"
DATA_DELETION_STATUS_COMPLETED = "completed"
DATA_DELETION_DEADLINE_DAYS = 30


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _calculate_deadline(requested_at: datetime) -> datetime:
    return _as_utc_aware(requested_at) + timedelta(days=DATA_DELETION_DEADLINE_DAYS)


def _as_utc_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def ensure_data_deletion_request_schema(bind: Engine) -> None:
    inspector = inspect(bind)
    if "data_deletion_requests" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("data_deletion_requests")}
    with bind.begin() as connection:
        if "deadline_at" not in existing_columns:
            connection.exec_driver_sql(
                "ALTER TABLE data_deletion_requests "
                "ADD COLUMN deadline_at DATETIME NULL"
            )

    refreshed_inspector = inspect(bind)
    existing_indexes = {index["name"] for index in refreshed_inspector.get_indexes("data_deletion_requests")}
    if "ix_data_deletion_requests_deadline_at" not in existing_indexes:
        with bind.begin() as connection:
            connection.exec_driver_sql(
                "CREATE INDEX ix_data_deletion_requests_deadline_at "
                "ON data_deletion_requests (deadline_at)"
            )


def _get_pending_request(db: Session, *, client_id: int) -> DataDeletionRequest | None:
    return (
        db.query(DataDeletionRequest)
        .filter(
            DataDeletionRequest.client_id == client_id,
            DataDeletionRequest.status == DATA_DELETION_STATUS_PENDING,
        )
        .order_by(DataDeletionRequest.id.desc())
        .first()
    )


# ======================
# Client-facing (MVP)
# ======================
def create_data_deletion_request(
    db: Session,
    *,
    client: User,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> DataDeletionRequest:
    ensure_data_deletion_request_schema(db.get_bind())

    pending = _get_pending_request(db, client_id=client.id)
    if pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="There is already a pending deletion request",
        )

    client_data = serialize_user(client)
    requested_at = _utcnow()
    deadline_at = requested_at + timedelta(days=DATA_DELETION_DEADLINE_DAYS)

    req = DataDeletionRequest(
        client_id=client.id,
        client_email=client_data["email"],
        client_name=client_data["name"],
        status=DATA_DELETION_STATUS_PENDING,
        requested_at=requested_at,
        deadline_at=deadline_at,
    )

    db.add(req)
    db.commit()
    db.refresh(req)
    log_action(
        db,
        user_id=client.id,
        action="DATA_DELETION_REQUEST",
        resource_type="data_deletion_request",
        resource_id=req.id,
        ip_address=ip_address,
        user_agent=user_agent,
        details={
            "client_id": client.id,
            "status": req.status,
            "deadline_at": deadline_at.isoformat(),
            "email": client_data["email"],
            "name": client_data["name"],
        },
    )
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
def execute_full_deletion(db: Session, *, client_id: int, execution_mode: str = "manual") -> None:
    """
    Ordem segura (FK):
      Feedback -> Reflections -> Dreams -> Anamnesis -> Consents -> TherapistClient -> (Request) -> User

    Mantém audit do pedido se o banco permitir:
      - marca completed
      - tenta SET NULL no client_id do request (precisa client_id nullable + FK ON DELETE SET NULL)
    Se não permitir, faz fallback:
      - remove o request antes de deletar o user (pra não travar).
    """

    ensure_data_deletion_request_schema(db.get_bind())

    req = _get_pending_request(db, client_id=client_id)
    request_id = req.id if req else None
    started_at = _utcnow()
    completed_at = None

    # 1) Feedback (subquery)
    reflection_ids_subq = select(Reflection.id).where(Reflection.client_id == client_id)
    feedback_deleted = db.execute(delete(Feedback).where(Feedback.reflection_id.in_(reflection_ids_subq))).rowcount or 0

    # 2) Reflections
    reflections_deleted = db.execute(delete(Reflection).where(Reflection.client_id == client_id)).rowcount or 0

    # 3) Dreams
    dreams_deleted = db.execute(delete(Dream).where(Dream.client_id == client_id)).rowcount or 0

    # 4) Anamnesis
    anamnesis_deleted = db.execute(delete(Anamnesis).where(Anamnesis.client_id == client_id)).rowcount or 0

    # 5) Consents  ✅ (NO SEU BANCO É client_id, NÃO user_id)
    consents_deleted = db.execute(delete(Consent).where(Consent.client_id == client_id)).rowcount or 0

    # 6) Push tokens / password reset tokens
    push_tokens_deleted = db.execute(delete(UserPushToken).where(UserPushToken.user_id == client_id)).rowcount or 0
    password_reset_tokens_deleted = (
        db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == client_id)).rowcount or 0
    )

    # 7) TherapistClient
    therapist_clients_deleted = (
        db.execute(delete(TherapistClient).where(TherapistClient.client_id == client_id)).rowcount or 0
    )

    # 8) Request: marcar completed + tentar manter audit
    if req:
        req.status = DATA_DELETION_STATUS_PROCESSING
        db.flush()

        req.status = DATA_DELETION_STATUS_COMPLETED
        completed_at = _utcnow()
        req.completed_at = completed_at

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
            feedback_deleted = db.execute(delete(Feedback).where(Feedback.reflection_id.in_(reflection_ids_subq))).rowcount or 0
            reflections_deleted = db.execute(delete(Reflection).where(Reflection.client_id == client_id)).rowcount or 0
            dreams_deleted = db.execute(delete(Dream).where(Dream.client_id == client_id)).rowcount or 0
            anamnesis_deleted = db.execute(delete(Anamnesis).where(Anamnesis.client_id == client_id)).rowcount or 0
            consents_deleted = db.execute(delete(Consent).where(Consent.client_id == client_id)).rowcount or 0
            push_tokens_deleted = db.execute(delete(UserPushToken).where(UserPushToken.user_id == client_id)).rowcount or 0
            password_reset_tokens_deleted = (
                db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == client_id)).rowcount or 0
            )
            therapist_clients_deleted = (
                db.execute(delete(TherapistClient).where(TherapistClient.client_id == client_id)).rowcount or 0
            )

            # marca completed (sem NULL) e apaga o request depois
            req = _get_pending_request(db, client_id=client_id)
            if req:
                req.status = DATA_DELETION_STATUS_COMPLETED
                completed_at = _utcnow()
                req.completed_at = completed_at
                db.flush()

            # remove requests do client antes de deletar user (para não travar FK)
            db.execute(delete(DataDeletionRequest).where(DataDeletionRequest.client_id == client_id))

    else:
        # sem request pendente, mas mesmo assim remove qualquer request do client (se existir)
        db.execute(delete(DataDeletionRequest).where(DataDeletionRequest.client_id == client_id))

    # 9) User
    users_deleted = db.execute(delete(User).where(User.id == client_id)).rowcount or 0

    db.commit()
    if completed_at is None:
        completed_at = _utcnow()

    log_action(
        db,
        action="DATA_DELETION_EXECUTED",
        resource_type="data_deletion_request",
        resource_id=request_id,
        details={
            "client_id": client_id,
            "execution_mode": execution_mode,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "deleted_counts": {
                "feedback": feedback_deleted,
                "reflections": reflections_deleted,
                "dreams": dreams_deleted,
                "anamnesis": anamnesis_deleted,
                "consents": consents_deleted,
                "user_push_tokens": push_tokens_deleted,
                "password_reset_tokens": password_reset_tokens_deleted,
                "therapist_clients": therapist_clients_deleted,
                "users": users_deleted,
            },
        },
    )


def process_due_deletion_requests(
    db: Session,
    *,
    dry_run: bool = False,
    limit: int | None = None,
) -> dict[str, int | bool]:
    ensure_data_deletion_request_schema(db.get_bind())

    now = _as_utc_aware(_utcnow())
    query = (
        db.query(DataDeletionRequest)
        .filter(
            DataDeletionRequest.status == DATA_DELETION_STATUS_PENDING,
        )
        .order_by(DataDeletionRequest.requested_at.asc(), DataDeletionRequest.id.asc())
    )

    pending_rows = query.all()
    rows = [
        row
        for row in pending_rows
        if _resolve_deadline(row) is not None and _resolve_deadline(row) <= now
    ]
    if limit is not None:
        rows = rows[:limit]
    due_request_count = len(rows)

    if dry_run:
        log_action(
            db,
            action="DATA_DELETION_DUE_DRY_RUN",
            resource_type="data_deletion_request",
            details={
                "due_request_count": due_request_count,
                "dry_run": True,
            },
        )
        return {"dry_run": True, "due_request_count": due_request_count, "processed_request_count": 0}

    processed = 0
    for row in rows:
        if row.client_id is None:
            continue
        execute_full_deletion(db, client_id=row.client_id, execution_mode="deadline_job")
        processed += 1

    log_action(
        db,
        action="DATA_DELETION_DUE_PROCESSED",
        resource_type="data_deletion_request",
        details={
            "due_request_count": due_request_count,
            "processed_request_count": processed,
            "dry_run": False,
        },
    )
    return {"dry_run": False, "due_request_count": due_request_count, "processed_request_count": processed}


def _resolve_deadline(row: DataDeletionRequest) -> datetime | None:
    if row.deadline_at is not None:
        return _as_utc_aware(row.deadline_at)
    if row.requested_at is None:
        return None
    return _calculate_deadline(row.requested_at)
