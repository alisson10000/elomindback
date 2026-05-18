from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.crypto import encrypt_text
from app.modules.anamnesis.model import Anamnesis
from app.modules.audit.model import AuditLog
from app.modules.auth.password_reset.model import PasswordResetToken
from app.modules.consents.model import Consent
from app.modules.data_retention.service import delete_expired_data, mark_therapy_as_ended
from app.modules.dreams.model import Dream
from app.modules.feedback.model import Feedback
from app.modules.push_tokens.model import UserPushToken
from app.modules.reflections.model import Reflection
from app.modules.data_retention import service as data_retention_service
from app.modules.therapist_clients.model import TherapistClient
from app.modules.therapist_clients.service import THERAPIST_CLIENT_STATUS_ACTIVE, THERAPIST_CLIENT_STATUS_ENDED
from app.modules.users.model import User


def _audit_rows(db_session, action: str) -> list[AuditLog]:
    with Session(bind=db_session.get_bind()) as audit_session:
        return (
            audit_session.query(AuditLog)
            .filter(AuditLog.action == action)
            .order_by(AuditLog.id.asc())
            .all()
        )


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _seed_client_payload(
    db_session,
    *,
    client_user: User,
    therapist_user: User,
    status: str,
    ended_at: datetime | None = None,
    content_prefix: str = "conteudo clinico",
) -> dict[str, int]:
    relationship = TherapistClient(
        therapist_id=therapist_user.id,
        client_id=client_user.id,
        status=status,
        ended_at=ended_at,
    )
    db_session.add(relationship)
    db_session.flush()

    reflection = Reflection(
        client_id=client_user.id,
        therapist_id=therapist_user.id,
        feeling_after_session=encrypt_text(f"{content_prefix} reflexao 1"),
        what_learned=encrypt_text(f"{content_prefix} reflexao 2"),
        positive_point=encrypt_text(f"{content_prefix} reflexao 3"),
        resistance_or_disagreement=encrypt_text(f"{content_prefix} reflexao 4"),
    )
    db_session.add(reflection)
    db_session.flush()

    feedback = Feedback(
        reflection_id=reflection.id,
        ia_generated_content=encrypt_text(f"{content_prefix} feedback"),
        ia_neuro_nutrition_tip=encrypt_text("dica segura"),
        ia_activity_suggestion=encrypt_text("atividade segura"),
        status="approved",
    )
    dream = Dream(
        client_id=client_user.id,
        therapist_id=therapist_user.id,
        description=encrypt_text(f"{content_prefix} sonho"),
        therapist_tags=encrypt_text("tag"),
        therapist_notes=encrypt_text("nota"),
    )
    anamnesis = Anamnesis(
        client_id=client_user.id,
        therapist_id=therapist_user.id,
        summary=encrypt_text(f"{content_prefix} anamnese"),
    )
    consent = Consent(client_id=client_user.id)
    push_token = UserPushToken(
        user_id=client_user.id,
        expo_push_token=f"ExponentPushToken[{client_user.id}]",
        platform="ios",
    )
    password_reset = PasswordResetToken(
        user_id=client_user.id,
        token_hash=f"token-hash-{client_user.id}",
        expires_at=_utcnow() + timedelta(days=1),
        used=False,
    )

    db_session.add_all([feedback, dream, anamnesis, consent, push_token, password_reset])
    db_session.commit()

    return {
        "relationship_id": relationship.id,
        "reflection_id": reflection.id,
        "feedback_id": feedback.id,
        "dream_id": dream.id,
        "anamnesis_id": anamnesis.id,
        "consent_id": consent.id,
        "push_token_id": push_token.id,
        "password_reset_id": password_reset.id,
    }


def test_old_audit_logs_are_removed(db_session):
    old_log = AuditLog(
        action="OLD_AUDIT",
        resource_type="audit",
        created_at=_utcnow() - timedelta(days=366),
        details='{"message":"old"}',
    )
    recent_log = AuditLog(
        action="RECENT_AUDIT",
        resource_type="audit",
        created_at=_utcnow() - timedelta(days=30),
        details='{"message":"recent"}',
    )
    db_session.add_all([old_log, recent_log])
    db_session.commit()

    summary = delete_expired_data(db_session)

    assert summary["deleted_counts"]["audit_logs"] == 1
    assert db_session.query(AuditLog).filter(AuditLog.action == "OLD_AUDIT").count() == 0
    assert db_session.query(AuditLog).filter(AuditLog.action == "RECENT_AUDIT").count() == 1


def test_audit_logs_use_12_calendar_months_boundary(db_session, monkeypatch):
    fixed_now = datetime(2026, 5, 18, 12, 0, 0)
    monkeypatch.setattr(data_retention_service, "_utcnow", lambda: fixed_now)

    old_log = AuditLog(
        action="BOUNDARY_OLD_AUDIT",
        resource_type="audit",
        created_at=datetime(2025, 5, 17, 12, 0, 0),
        details='{"message":"old"}',
    )
    boundary_log = AuditLog(
        action="BOUNDARY_KEEP_AUDIT",
        resource_type="audit",
        created_at=datetime(2025, 5, 18, 12, 0, 0),
        details='{"message":"keep"}',
    )
    db_session.add_all([old_log, boundary_log])
    db_session.commit()

    summary = delete_expired_data(db_session)

    assert summary["deleted_counts"]["audit_logs"] == 1
    assert db_session.query(AuditLog).filter(AuditLog.action == "BOUNDARY_OLD_AUDIT").count() == 0
    assert db_session.query(AuditLog).filter(AuditLog.action == "BOUNDARY_KEEP_AUDIT").count() == 1


def test_recent_audit_logs_are_preserved(db_session):
    recent_log = AuditLog(
        action="ONLY_RECENT_AUDIT",
        resource_type="audit",
        created_at=_utcnow() - timedelta(days=10),
        details='{"message":"recent"}',
    )
    db_session.add(recent_log)
    db_session.commit()

    summary = delete_expired_data(db_session)

    assert summary["deleted_counts"]["audit_logs"] == 0
    assert db_session.query(AuditLog).filter(AuditLog.action == "ONLY_RECENT_AUDIT").count() == 1


def test_active_client_data_is_not_deleted(db_session, user_factory):
    therapist = user_factory(email="retention-active-therapist@example.com", role="therapist")
    client_user = user_factory(email="retention-active-client@example.com")
    _seed_client_payload(
        db_session,
        client_user=client_user,
        therapist_user=therapist,
        status=THERAPIST_CLIENT_STATUS_ACTIVE,
        content_prefix="ativo",
    )

    summary = delete_expired_data(db_session)

    assert summary["expired_client_count"] == 0
    assert db_session.query(Reflection).filter(Reflection.client_id == client_user.id).count() == 1
    assert db_session.query(Feedback).count() == 1
    assert db_session.query(Dream).filter(Dream.client_id == client_user.id).count() == 1
    assert db_session.query(Anamnesis).filter(Anamnesis.client_id == client_user.id).count() == 1
    assert db_session.query(Consent).filter(Consent.client_id == client_user.id).count() == 1
    assert db_session.query(UserPushToken).filter(UserPushToken.user_id == client_user.id).count() == 1
    assert db_session.query(PasswordResetToken).filter(PasswordResetToken.user_id == client_user.id).count() == 1
    assert db_session.query(TherapistClient).filter(TherapistClient.client_id == client_user.id).count() == 1


def test_recently_ended_client_data_is_not_deleted(db_session, user_factory):
    therapist = user_factory(email="retention-recent-ended-therapist@example.com", role="therapist")
    client_user = user_factory(email="retention-recent-ended-client@example.com")
    _seed_client_payload(
        db_session,
        client_user=client_user,
        therapist_user=therapist,
        status=THERAPIST_CLIENT_STATUS_ENDED,
        ended_at=_utcnow() - timedelta(days=500),
        content_prefix="encerrado-recente",
    )

    summary = delete_expired_data(db_session)

    assert summary["expired_client_count"] == 0
    assert db_session.query(Reflection).filter(Reflection.client_id == client_user.id).count() == 1
    assert db_session.query(Feedback).count() == 1
    assert db_session.query(Dream).filter(Dream.client_id == client_user.id).count() == 1
    assert db_session.query(Anamnesis).filter(Anamnesis.client_id == client_user.id).count() == 1
    assert db_session.query(Consent).filter(Consent.client_id == client_user.id).count() == 1
    assert db_session.query(UserPushToken).filter(UserPushToken.user_id == client_user.id).count() == 1
    assert db_session.query(PasswordResetToken).filter(PasswordResetToken.user_id == client_user.id).count() == 1
    assert db_session.query(TherapistClient).filter(TherapistClient.client_id == client_user.id).count() == 1


def test_expired_client_data_is_deleted_without_deleting_user(db_session, user_factory):
    therapist = user_factory(email="retention-expired-therapist@example.com", role="therapist")
    client_user = user_factory(email="retention-expired-client@example.com")
    _seed_client_payload(
        db_session,
        client_user=client_user,
        therapist_user=therapist,
        status=THERAPIST_CLIENT_STATUS_ENDED,
        ended_at=_utcnow() - timedelta(days=800),
        content_prefix="encerrado-antigo",
    )

    summary = delete_expired_data(db_session)

    assert summary["expired_client_count"] == 1
    assert summary["deleted_counts"]["feedback"] == 1
    assert summary["deleted_counts"]["reflections"] == 1
    assert summary["deleted_counts"]["dreams"] == 1
    assert summary["deleted_counts"]["anamnesis"] == 1
    assert summary["deleted_counts"]["consents"] == 1
    assert summary["deleted_counts"]["user_push_tokens"] == 1
    assert summary["deleted_counts"]["password_reset_tokens"] == 1
    assert summary["deleted_counts"]["therapist_clients"] == 1
    assert db_session.query(User).filter(User.id == client_user.id).count() == 1
    assert db_session.query(Reflection).filter(Reflection.client_id == client_user.id).count() == 0
    assert db_session.query(Feedback).count() == 0
    assert db_session.query(Dream).filter(Dream.client_id == client_user.id).count() == 0
    assert db_session.query(Anamnesis).filter(Anamnesis.client_id == client_user.id).count() == 0
    assert db_session.query(Consent).filter(Consent.client_id == client_user.id).count() == 0
    assert db_session.query(UserPushToken).filter(UserPushToken.user_id == client_user.id).count() == 0
    assert db_session.query(PasswordResetToken).filter(PasswordResetToken.user_id == client_user.id).count() == 0
    assert db_session.query(TherapistClient).filter(TherapistClient.client_id == client_user.id).count() == 0


def test_ended_client_uses_2_calendar_year_boundary(db_session, user_factory, monkeypatch):
    fixed_now = datetime(2026, 5, 18, 12, 0, 0)
    monkeypatch.setattr(data_retention_service, "_utcnow", lambda: fixed_now)

    therapist = user_factory(email="retention-boundary-therapist@example.com", role="therapist")
    expired_client = user_factory(email="retention-boundary-expired@example.com")
    boundary_client = user_factory(email="retention-boundary-keep@example.com")

    _seed_client_payload(
        db_session,
        client_user=expired_client,
        therapist_user=therapist,
        status=THERAPIST_CLIENT_STATUS_ENDED,
        ended_at=datetime(2024, 5, 17, 11, 59, 59),
        content_prefix="expira",
    )
    _seed_client_payload(
        db_session,
        client_user=boundary_client,
        therapist_user=therapist,
        status=THERAPIST_CLIENT_STATUS_ENDED,
        ended_at=datetime(2024, 5, 18, 12, 0, 0),
        content_prefix="mantem",
    )

    summary = delete_expired_data(db_session)

    assert summary["expired_client_count"] == 1
    assert db_session.query(Reflection).filter(Reflection.client_id == expired_client.id).count() == 0
    assert db_session.query(Reflection).filter(Reflection.client_id == boundary_client.id).count() == 1
    assert db_session.query(TherapistClient).filter(TherapistClient.client_id == expired_client.id).count() == 0
    assert db_session.query(TherapistClient).filter(TherapistClient.client_id == boundary_client.id).count() == 1


def test_dry_run_does_not_delete_anything(db_session, user_factory):
    therapist = user_factory(email="retention-dry-run-therapist@example.com", role="therapist")
    client_user = user_factory(email="retention-dry-run-client@example.com")
    _seed_client_payload(
        db_session,
        client_user=client_user,
        therapist_user=therapist,
        status=THERAPIST_CLIENT_STATUS_ENDED,
        ended_at=_utcnow() - timedelta(days=900),
        content_prefix="dry-run",
    )

    summary = delete_expired_data(db_session, dry_run=True)

    assert summary["dry_run"] is True
    assert summary["expired_client_count"] == 1
    assert summary["deleted_counts"]["feedback"] == 1
    assert db_session.query(Reflection).filter(Reflection.client_id == client_user.id).count() == 1
    assert db_session.query(Feedback).count() == 1
    assert db_session.query(Dream).filter(Dream.client_id == client_user.id).count() == 1
    assert db_session.query(Anamnesis).filter(Anamnesis.client_id == client_user.id).count() == 1
    assert db_session.query(Consent).filter(Consent.client_id == client_user.id).count() == 1
    assert db_session.query(UserPushToken).filter(UserPushToken.user_id == client_user.id).count() == 1
    assert db_session.query(PasswordResetToken).filter(PasswordResetToken.user_id == client_user.id).count() == 1
    assert db_session.query(TherapistClient).filter(TherapistClient.client_id == client_user.id).count() == 1


def test_retention_job_logs_only_safe_counts(db_session, user_factory):
    therapist = user_factory(email="retention-log-therapist@example.com", role="therapist")
    client_user = user_factory(email="retention-log-client@example.com")
    sensitive_phrase = "historia clinica ultra sensivel"
    _seed_client_payload(
        db_session,
        client_user=client_user,
        therapist_user=therapist,
        status=THERAPIST_CLIENT_STATUS_ENDED,
        ended_at=_utcnow() - timedelta(days=900),
        content_prefix=sensitive_phrase,
    )

    delete_expired_data(db_session)

    rows = _audit_rows(db_session, "DATA_RETENTION_EXECUTED")
    assert len(rows) == 1
    assert rows[0].details is not None
    assert sensitive_phrase not in rows[0].details
    assert client_user.email not in rows[0].details
    assert client_user.name not in rows[0].details
    assert "expired_client_count" in rows[0].details
    assert "deleted_counts" in rows[0].details


def test_mark_therapy_as_ended_updates_relationship_and_audits(db_session, user_factory):
    therapist = user_factory(email="retention-end-therapist@example.com", role="therapist")
    client_user = user_factory(email="retention-end-client@example.com")
    relationship = TherapistClient(
        therapist_id=therapist.id,
        client_id=client_user.id,
        status=THERAPIST_CLIENT_STATUS_ACTIVE,
        ended_at=None,
    )
    db_session.add(relationship)
    db_session.commit()

    updated = mark_therapy_as_ended(db_session, therapist.id, client_user.id)

    assert updated.id == relationship.id
    assert updated.status == THERAPIST_CLIENT_STATUS_ENDED
    assert updated.ended_at is not None

    rows = _audit_rows(db_session, "THERAPY_ENDED")
    assert len(rows) == 1
    assert rows[0].user_id == therapist.id
    assert rows[0].resource_id == relationship.id
