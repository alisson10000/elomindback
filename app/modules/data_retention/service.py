from __future__ import annotations

import calendar
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, delete, exists, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.modules.anamnesis.model import Anamnesis
from app.modules.audit.model import AuditLog
from app.modules.audit.service import log_action
from app.modules.auth.password_reset.model import PasswordResetToken
from app.modules.consents.model import Consent
from app.modules.dreams.model import Dream
from app.modules.feedback.model import Feedback
from app.modules.push_tokens.model import UserPushToken
from app.modules.reflections.model import Reflection
from app.modules.therapist_clients.model import TherapistClient
from app.modules.therapist_clients.service import (
    THERAPIST_CLIENT_STATUS_ACTIVE,
    THERAPIST_CLIENT_STATUS_ENDED,
)

AUDIT_LOG_RETENTION_MONTHS = 12
THERAPY_RETENTION_YEARS = 2
DELETE_CONSENTS_ON_RETENTION_EXPIRY = True


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def delete_expired_data(db: Session, dry_run: bool = False) -> dict[str, Any]:
    now = _utcnow()
    audit_cutoff = _subtract_months(now, AUDIT_LOG_RETENTION_MONTHS)
    therapy_cutoff = _subtract_years(now, THERAPY_RETENTION_YEARS)
    expired_client_ids = _get_expired_client_ids(db, therapy_cutoff)

    reflection_ids_subquery = select(Reflection.id).where(Reflection.client_id.in_(expired_client_ids))

    summary = {
        "dry_run": dry_run,
        "executed_at": now.isoformat(),
        "audit_log_cutoff": audit_cutoff.isoformat(),
        "therapy_cutoff": therapy_cutoff.isoformat(),
        "expired_client_count": len(expired_client_ids),
        "expired_relationship_count": _count_rows(
            db,
            select(func.count())
            .select_from(TherapistClient)
            .where(TherapistClient.client_id.in_(expired_client_ids)),
        ),
        "deleted_counts": {
            "audit_logs": _count_rows(
                db,
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.created_at < audit_cutoff),
            ),
            "feedback": _count_rows(
                db,
                select(func.count())
                .select_from(Feedback)
                .where(Feedback.reflection_id.in_(reflection_ids_subquery)),
            ),
            "reflections": _count_rows(
                db,
                select(func.count())
                .select_from(Reflection)
                .where(Reflection.client_id.in_(expired_client_ids)),
            ),
            "dreams": _count_rows(
                db,
                select(func.count())
                .select_from(Dream)
                .where(Dream.client_id.in_(expired_client_ids)),
            ),
            "anamnesis": _count_rows(
                db,
                select(func.count())
                .select_from(Anamnesis)
                .where(Anamnesis.client_id.in_(expired_client_ids)),
            ),
            "consents": _count_rows(
                db,
                select(func.count())
                .select_from(Consent)
                .where(Consent.client_id.in_(expired_client_ids)),
            )
            if DELETE_CONSENTS_ON_RETENTION_EXPIRY
            else 0,
            "user_push_tokens": _count_rows(
                db,
                select(func.count())
                .select_from(UserPushToken)
                .where(UserPushToken.user_id.in_(expired_client_ids)),
            ),
            "password_reset_tokens": _count_rows(
                db,
                select(func.count())
                .select_from(PasswordResetToken)
                .where(PasswordResetToken.user_id.in_(expired_client_ids)),
            ),
            "therapist_clients": _count_rows(
                db,
                select(func.count())
                .select_from(TherapistClient)
                .where(TherapistClient.client_id.in_(expired_client_ids)),
            ),
        },
    }

    if dry_run:
        _log_retention_execution(db, action="DATA_RETENTION_DRY_RUN", summary=summary)
        return summary

    try:
        db.execute(delete(AuditLog).where(AuditLog.created_at < audit_cutoff))

        if expired_client_ids:
            db.execute(delete(Feedback).where(Feedback.reflection_id.in_(reflection_ids_subquery)))
            db.execute(delete(Reflection).where(Reflection.client_id.in_(expired_client_ids)))
            db.execute(delete(Dream).where(Dream.client_id.in_(expired_client_ids)))
            db.execute(delete(Anamnesis).where(Anamnesis.client_id.in_(expired_client_ids)))
            if DELETE_CONSENTS_ON_RETENTION_EXPIRY:
                db.execute(delete(Consent).where(Consent.client_id.in_(expired_client_ids)))
            db.execute(delete(UserPushToken).where(UserPushToken.user_id.in_(expired_client_ids)))
            db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id.in_(expired_client_ids)))
            db.execute(delete(TherapistClient).where(TherapistClient.client_id.in_(expired_client_ids)))

        db.commit()
    except Exception:
        db.rollback()
        raise

    _log_retention_execution(db, action="DATA_RETENTION_EXECUTED", summary=summary)
    return summary


def mark_therapy_as_ended(db: Session, therapist_id: int, client_id: int) -> TherapistClient:
    relationship = (
        db.query(TherapistClient)
        .filter(
            TherapistClient.therapist_id == therapist_id,
            TherapistClient.client_id == client_id,
            TherapistClient.status == THERAPIST_CLIENT_STATUS_ACTIVE,
        )
        .order_by(TherapistClient.id.desc())
        .first()
    )

    if relationship is None:
        relationship = (
            db.query(TherapistClient)
            .filter(
                TherapistClient.therapist_id == therapist_id,
                TherapistClient.client_id == client_id,
            )
            .order_by(TherapistClient.id.desc())
            .first()
        )
        if relationship is None:
            raise ValueError("Therapist-client relationship not found")
        return relationship

    relationship.status = THERAPIST_CLIENT_STATUS_ENDED
    relationship.ended_at = _utcnow()

    db.commit()
    db.refresh(relationship)

    log_action(
        db,
        user_id=therapist_id,
        action="THERAPY_ENDED",
        resource_type="therapist_client",
        resource_id=relationship.id,
        details={
            "client_id": client_id,
            "status": relationship.status,
            "ended_at": relationship.ended_at.isoformat() if relationship.ended_at else None,
        },
    )
    return relationship


def _get_expired_client_ids(db: Session, therapy_cutoff: datetime) -> list[int]:
    current = aliased(TherapistClient)
    active_relationship_exists = exists(
        select(1).where(
            and_(
                current.client_id == TherapistClient.client_id,
                current.status == THERAPIST_CLIENT_STATUS_ACTIVE,
            )
        )
    )
    fresh_ended_relationship_exists = exists(
        select(1).where(
            and_(
                current.client_id == TherapistClient.client_id,
                current.status == THERAPIST_CLIENT_STATUS_ENDED,
                or_(current.ended_at.is_(None), current.ended_at >= therapy_cutoff),
            )
        )
    )

    rows = db.execute(
        select(TherapistClient.client_id)
        .where(
            TherapistClient.status == THERAPIST_CLIENT_STATUS_ENDED,
            TherapistClient.ended_at.is_not(None),
            TherapistClient.ended_at < therapy_cutoff,
            ~active_relationship_exists,
            ~fresh_ended_relationship_exists,
        )
        .group_by(TherapistClient.client_id)
    ).all()
    return [row[0] for row in rows]


def _count_rows(db: Session, statement) -> int:
    value = db.execute(statement).scalar_one()
    return int(value or 0)


def _subtract_months(value: datetime, months: int) -> datetime:
    total_months = (value.year * 12 + value.month - 1) - months
    year = total_months // 12
    month = total_months % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _subtract_years(value: datetime, years: int) -> datetime:
    year = value.year - years
    day = min(value.day, calendar.monthrange(year, value.month)[1])
    return value.replace(year=year, day=day)


def _log_retention_execution(db: Session, *, action: str, summary: dict[str, Any]) -> None:
    deleted_counts = summary["deleted_counts"]
    log_action(
        db,
        action=action,
        resource_type="data_retention",
        details={
            "dry_run": summary["dry_run"],
            "expired_client_count": summary["expired_client_count"],
            "expired_relationship_count": summary["expired_relationship_count"],
            "deleted_counts": {
                "audit_logs": deleted_counts["audit_logs"],
                "feedback": deleted_counts["feedback"],
                "reflections": deleted_counts["reflections"],
                "dreams": deleted_counts["dreams"],
                "anamnesis": deleted_counts["anamnesis"],
                "consents": deleted_counts["consents"],
                "user_push_tokens": deleted_counts["user_push_tokens"],
                "password_reset_tokens": deleted_counts["password_reset_tokens"],
                "therapist_clients": deleted_counts["therapist_clients"],
            },
        },
    )
