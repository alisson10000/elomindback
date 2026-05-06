from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.crypto import encrypt_text
from app.modules.feedback.model import Feedback
from app.modules.reflections.model import Reflection
from app.modules.therapist_clients.service import link_therapist_client
from app.modules.audit.model import AuditLog


def _load_audit_rows(db_session, action: str) -> list[AuditLog]:
    with Session(bind=db_session.get_bind()) as audit_session:
        return (
            audit_session.query(AuditLog)
            .filter(AuditLog.action == action)
            .order_by(AuditLog.id.asc())
            .all()
        )


def _create_reflection_via_api(client, auth_headers, client_user):
    response = client.post(
        "/reflections/",
        json={
            "feeling_after_session": "Me senti melhor",
            "what_learned": "Aprendi a respirar",
            "positive_point": "Consegui conversar",
            "resistance_or_disagreement": "Nenhuma",
        },
        headers={
            **auth_headers(client_user),
            "User-Agent": "pytest-reflection-agent",
            "X-Forwarded-For": "203.0.113.60",
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_pending_feedback(db_session, reflection_id: int) -> Feedback:
    feedback = Feedback(
        reflection_id=reflection_id,
        ia_generated_content=encrypt_text("Texto de apoio inicial"),
        ia_neuro_nutrition_tip=encrypt_text("Dica neuro"),
        ia_activity_suggestion=encrypt_text("Atividade"),
        status="pending_approval",
    )
    db_session.add(feedback)
    db_session.commit()
    db_session.refresh(feedback)
    return feedback


def test_logout_is_audited(client, user_factory, auth_headers, db_session):
    user = user_factory(email="logout@example.com", password="StrongPass123")

    response = client.post(
        "/auth/logout",
        headers={
            **auth_headers(user),
            "User-Agent": "pytest-logout-agent",
            "X-Forwarded-For": "198.51.100.60",
        },
    )

    assert response.status_code == 200

    rows = _load_audit_rows(db_session, "LOGOUT")
    assert len(rows) == 1
    assert rows[0].user_id == user.id
    assert rows[0].ip_address == "198.51.100.60"


def test_consent_accepted_is_audited(client, user_factory, auth_headers, db_session):
    client_user = user_factory(email="consent@example.com", password="StrongPass123")

    response = client.post(
        "/consents",
        json={"accepted": True},
        headers={
            **auth_headers(client_user),
            "User-Agent": "pytest-consent-agent",
            "X-Forwarded-For": "198.51.100.61",
        },
    )

    assert response.status_code == 200

    rows = _load_audit_rows(db_session, "CONSENT_ACCEPTED")
    assert len(rows) == 1
    assert rows[0].user_id == client_user.id
    assert rows[0].ip_address == "198.51.100.61"


def test_reflection_updated_is_audited(client, user_factory, auth_headers, db_session):
    client_user = user_factory(email="reflection-update@example.com", password="StrongPass123")
    created = _create_reflection_via_api(client, auth_headers, client_user)

    response = client.patch(
        f"/reflections/{created['id']}",
        json={
            "feeling_after_session": "Agora estou mais calmo",
            "what_learned": "Aprendi a pausar",
            "positive_point": "Escutei melhor",
            "resistance_or_disagreement": "Sem resistencia",
        },
        headers={
            **auth_headers(client_user),
            "User-Agent": "pytest-reflection-update-agent",
            "X-Forwarded-For": "198.51.100.62",
        },
    )

    assert response.status_code == 200

    rows = _load_audit_rows(db_session, "REFLECTION_UPDATED")
    assert len(rows) == 1
    assert rows[0].user_id == client_user.id
    assert rows[0].resource_id == created["id"]
    assert rows[0].ip_address == "198.51.100.62"


def test_reflection_deleted_is_audited(client, user_factory, auth_headers, db_session):
    client_user = user_factory(email="reflection-delete@example.com", password="StrongPass123")
    created = _create_reflection_via_api(client, auth_headers, client_user)

    response = client.delete(
        f"/reflections/{created['id']}",
        headers={
            **auth_headers(client_user),
            "User-Agent": "pytest-reflection-delete-agent",
            "X-Forwarded-For": "198.51.100.63",
        },
    )

    assert response.status_code == 200

    rows = _load_audit_rows(db_session, "REFLECTION_DELETED")
    assert len(rows) == 1
    assert rows[0].user_id == client_user.id
    assert rows[0].resource_id == created["id"]
    assert rows[0].ip_address == "198.51.100.63"


def test_feedback_approved_is_audited(client, user_factory, auth_headers, db_session, monkeypatch):
    therapist = user_factory(
        email="feedback-approve-therapist@example.com",
        name="Therapist Approve",
        role="therapist",
        password="StrongPass123",
    )
    client_user = user_factory(
        email="feedback-approve-client@example.com",
        password="StrongPass123",
    )
    link_therapist_client(db_session, therapist_id=therapist.id, client_id=client_user.id)
    monkeypatch.setattr("app.modules.feedback.service._notify_client_feedback_approved", lambda *args, **kwargs: None)

    created = _create_reflection_via_api(client, auth_headers, client_user)
    feedback = _create_pending_feedback(db_session, created["id"])

    response = client.patch(
        f"/feedback/{feedback.id}/approve",
        json={"therapist_notes": "Aprovado com ajuste"},
        headers={
            **auth_headers(therapist),
            "User-Agent": "pytest-feedback-approve-agent",
            "X-Forwarded-For": "198.51.100.64",
        },
    )

    assert response.status_code == 200

    rows = _load_audit_rows(db_session, "FEEDBACK_APPROVED")
    assert len(rows) == 1
    assert rows[0].user_id == therapist.id
    assert rows[0].resource_id == feedback.id
    assert rows[0].ip_address == "198.51.100.64"


def test_feedback_rejected_is_audited(client, user_factory, auth_headers, db_session):
    therapist = user_factory(
        email="feedback-reject-therapist@example.com",
        name="Therapist Reject",
        role="therapist",
        password="StrongPass123",
    )
    client_user = user_factory(
        email="feedback-reject-client@example.com",
        password="StrongPass123",
    )
    link_therapist_client(db_session, therapist_id=therapist.id, client_id=client_user.id)

    created = _create_reflection_via_api(client, auth_headers, client_user)
    feedback = _create_pending_feedback(db_session, created["id"])

    response = client.patch(
        f"/feedback/{feedback.id}/reject",
        json={"therapist_notes": "Rejeitado para reescrita"},
        headers={
            **auth_headers(therapist),
            "User-Agent": "pytest-feedback-reject-agent",
            "X-Forwarded-For": "198.51.100.65",
        },
    )

    assert response.status_code == 200

    rows = _load_audit_rows(db_session, "FEEDBACK_REJECTED")
    assert len(rows) == 1
    assert rows[0].user_id == therapist.id
    assert rows[0].resource_id == feedback.id
    assert rows[0].ip_address == "198.51.100.65"


def test_anamnesis_events_are_audited(client, user_factory, auth_headers, db_session):
    therapist = user_factory(
        email="anamnesis-therapist@example.com",
        name="Therapist Anamnesis",
        role="therapist",
        password="StrongPass123",
    )
    client_user = user_factory(
        email="anamnesis-client@example.com",
        password="StrongPass123",
    )

    create_response = client.post(
        f"/anamnesis/{client_user.id}",
        json={"summary": "Resumo clinico sensivel"},
        headers={
            **auth_headers(therapist),
            "User-Agent": "pytest-anamnesis-create-agent",
            "X-Forwarded-For": "198.51.100.66",
        },
    )
    assert create_response.status_code == 200

    view_response = client.get(
        f"/anamnesis/{client_user.id}",
        headers={
            **auth_headers(therapist),
            "User-Agent": "pytest-anamnesis-view-agent",
            "X-Forwarded-For": "198.51.100.67",
        },
    )
    assert view_response.status_code == 200

    update_response = client.patch(
        f"/anamnesis/{client_user.id}",
        json={"summary": "Resumo clinico atualizado"},
        headers={
            **auth_headers(therapist),
            "User-Agent": "pytest-anamnesis-update-agent",
            "X-Forwarded-For": "198.51.100.68",
        },
    )
    assert update_response.status_code == 200

    created_rows = _load_audit_rows(db_session, "ANAMNESIS_CREATED")
    viewed_rows = _load_audit_rows(db_session, "ANAMNESIS_VIEWED")
    updated_rows = _load_audit_rows(db_session, "ANAMNESIS_UPDATED")

    assert len(created_rows) == 1
    assert len(viewed_rows) == 1
    assert len(updated_rows) == 1
    assert created_rows[0].user_id == therapist.id
    assert viewed_rows[0].ip_address == "198.51.100.67"
    assert updated_rows[0].ip_address == "198.51.100.68"


def test_invitation_events_are_audited(client, user_factory, auth_headers, db_session):
    therapist = user_factory(
        email="invite-therapist@example.com",
        name="Therapist Invite",
        role="therapist",
        password="StrongPass123",
    )

    import app.modules.invitations.router as invitations_router

    invitations_router.send_email = lambda *args, **kwargs: None

    create_response = client.post(
        "/invitations",
        json={"email": "invited-client@example.com"},
        headers={
            **auth_headers(therapist),
            "User-Agent": "pytest-invitation-create-agent",
            "X-Forwarded-For": "198.51.100.69",
        },
    )
    assert create_response.status_code == 200

    from app.modules.invitations.service import create_invitation

    _, token = create_invitation(
        db_session,
        therapist_id=therapist.id,
        email="signup-client@example.com",
    )

    signup_response = client.post(
        "/invitations/signup",
        json={
            "token": token,
            "name": "Client Via Invite",
            "password": "StrongPass123",
        },
        headers={
            "User-Agent": "pytest-invitation-used-agent",
            "X-Forwarded-For": "198.51.100.70",
        },
    )
    assert signup_response.status_code == 200

    created_rows = _load_audit_rows(db_session, "INVITATION_CREATED")
    used_rows = _load_audit_rows(db_session, "INVITATION_USED")

    assert len(created_rows) >= 1
    assert len(used_rows) == 1
    assert created_rows[0].user_id == therapist.id
    assert used_rows[0].ip_address == "198.51.100.70"


def test_data_deletion_request_is_audited(client, user_factory, auth_headers, db_session):
    client_user = user_factory(email="lgpd-delete@example.com", password="StrongPass123")

    response = client.post(
        "/data-deletion-request",
        headers={
            **auth_headers(client_user),
            "User-Agent": "pytest-data-delete-agent",
            "X-Forwarded-For": "198.51.100.71",
        },
    )

    assert response.status_code == 200

    rows = _load_audit_rows(db_session, "DATA_DELETION_REQUEST")
    assert len(rows) == 1
    assert rows[0].user_id == client_user.id
    assert rows[0].ip_address == "198.51.100.71"
