from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.crypto import encrypt_text
from app.modules.anamnesis.model import Anamnesis
from app.modules.audit.model import AuditLog
from app.modules.auth.password_reset.model import PasswordResetToken
from app.modules.consents.model import Consent
from app.modules.data_deletion_requests.model import DataDeletionRequest
from app.modules.data_deletion_requests.service import (
    DATA_DELETION_DEADLINE_DAYS,
    create_data_deletion_request,
    execute_full_deletion,
    process_due_deletion_requests,
)
from app.modules.dreams.model import Dream
from app.modules.feedback.model import Feedback
from app.modules.push_tokens.model import UserPushToken
from app.modules.reflections.model import Reflection
from app.modules.therapist_clients.model import TherapistClient
from app.modules.users.model import User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _load_audit_rows(db_session, action: str) -> list[AuditLog]:
    with Session(bind=db_session.get_bind()) as audit_session:
        return (
            audit_session.query(AuditLog)
            .filter(AuditLog.action == action)
            .order_by(AuditLog.id.asc())
            .all()
        )


def _seed_deletion_payload(db_session, *, client_user: User, therapist_user: User, content_prefix: str) -> None:
    relationship = TherapistClient(
        therapist_id=therapist_user.id,
        client_id=client_user.id,
    )
    db_session.add(relationship)
    db_session.flush()

    reflection = Reflection(
        client_id=client_user.id,
        therapist_id=therapist_user.id,
        feeling_after_session=encrypt_text(f"{content_prefix} reflexao"),
        what_learned=encrypt_text(f"{content_prefix} aprendizado"),
        positive_point=encrypt_text(f"{content_prefix} positivo"),
        resistance_or_disagreement=encrypt_text(f"{content_prefix} resistencia"),
    )
    db_session.add(reflection)
    db_session.flush()

    db_session.add(
        Feedback(
            reflection_id=reflection.id,
            ia_generated_content=encrypt_text(f"{content_prefix} feedback"),
            ia_neuro_nutrition_tip=encrypt_text("dica"),
            ia_activity_suggestion=encrypt_text("atividade"),
            status="approved",
        )
    )
    db_session.add(
        Dream(
            client_id=client_user.id,
            therapist_id=therapist_user.id,
            description=encrypt_text(f"{content_prefix} sonho"),
            therapist_tags=encrypt_text("tag"),
            therapist_notes=encrypt_text("nota"),
        )
    )
    db_session.add(
        Anamnesis(
            client_id=client_user.id,
            therapist_id=therapist_user.id,
            summary=encrypt_text(f"{content_prefix} anamnese"),
        )
    )
    db_session.add(Consent(client_id=client_user.id))
    db_session.add(
        UserPushToken(
            user_id=client_user.id,
            expo_push_token=f"ExponentPushToken[{client_user.id}]",
            platform="android",
        )
    )
    db_session.add(
        PasswordResetToken(
            user_id=client_user.id,
            token_hash=f"reset-{client_user.id}",
            expires_at=_utcnow() + timedelta(days=1),
            used=False,
        )
    )
    db_session.commit()


def test_create_data_deletion_request_sets_internal_deadline(db_session, user_factory):
    client_user = user_factory(email="deadline-client@example.com", password="StrongPass123")

    req = create_data_deletion_request(db_session, client=client_user)

    assert req.status == "pending"
    assert req.deadline_at is not None
    assert req.requested_at is not None
    assert req.deadline_at - req.requested_at == timedelta(days=DATA_DELETION_DEADLINE_DAYS)


def test_process_due_deletion_requests_only_executes_overdue_items(db_session, user_factory):
    therapist = user_factory(email="job-therapist@example.com", role="therapist", password="StrongPass123")
    due_client = user_factory(email="job-due@example.com", password="StrongPass123")
    future_client = user_factory(email="job-future@example.com", password="StrongPass123")

    _seed_deletion_payload(db_session, client_user=due_client, therapist_user=therapist, content_prefix="sensivel due")
    _seed_deletion_payload(db_session, client_user=future_client, therapist_user=therapist, content_prefix="sensivel future")

    due_request = create_data_deletion_request(db_session, client=due_client)
    future_request = create_data_deletion_request(db_session, client=future_client)

    due_request.deadline_at = _utcnow() - timedelta(days=1)
    future_request.deadline_at = _utcnow() + timedelta(days=5)
    db_session.commit()

    summary = process_due_deletion_requests(db_session)

    assert summary == {"dry_run": False, "due_request_count": 1, "processed_request_count": 1}
    assert db_session.query(User).filter(User.id == due_client.id).count() == 0
    assert db_session.query(User).filter(User.id == future_client.id).count() == 1

    kept_request = db_session.query(DataDeletionRequest).filter(DataDeletionRequest.id == future_request.id).one()
    assert kept_request.status == "pending"


def test_hard_delete_execution_is_audited_without_sensitive_content(db_session, user_factory):
    therapist = user_factory(email="audit-delete-therapist@example.com", role="therapist", password="StrongPass123")
    client_user = user_factory(email="audit-delete-client@example.com", password="StrongPass123")
    sensitive_text = "historia clinica muito sigilosa"

    _seed_deletion_payload(
        db_session,
        client_user=client_user,
        therapist_user=therapist,
        content_prefix=sensitive_text,
    )
    req = create_data_deletion_request(db_session, client=client_user)

    execute_full_deletion(db_session, client_id=client_user.id)

    rows = _load_audit_rows(db_session, "DATA_DELETION_EXECUTED")
    assert len(rows) == 1
    assert rows[0].resource_id == req.id
    assert rows[0].details is not None
    assert sensitive_text not in rows[0].details
    assert client_user.email not in rows[0].details
    assert client_user.name not in rows[0].details
    assert '"user_push_tokens": 1' in rows[0].details
    assert '"password_reset_tokens": 1' in rows[0].details

    stored_request = db_session.query(DataDeletionRequest).filter(DataDeletionRequest.id == req.id).one_or_none()
    assert stored_request is not None
    assert stored_request.status == "completed"
    assert stored_request.client_id is None
