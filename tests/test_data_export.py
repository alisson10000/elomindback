from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from app.core.crypto import encrypt_text
from app.core.rate_limit import limiter
from app.modules.audit.model import AuditLog
from app.modules.consents.model import Consent
from app.modules.dreams.model import Dream
from app.modules.feedback.model import Feedback
from app.modules.reflections.model import Reflection


@pytest.fixture(autouse=True)
def reset_limiter_state():
    limiter.reset()
    yield
    limiter.reset()


def _load_audit_rows(db_session, action: str) -> list[AuditLog]:
    with Session(bind=db_session.get_bind()) as audit_session:
        return (
            audit_session.query(AuditLog)
            .filter(AuditLog.action == action)
            .order_by(AuditLog.id.asc())
            .all()
        )


def _seed_export_data(db_session, *, client_user, therapist_user, other_user):
    consent = Consent(client_id=client_user.id)
    db_session.add(consent)
    db_session.flush()

    my_reflection = Reflection(
        client_id=client_user.id,
        therapist_id=therapist_user.id,
        feeling_after_session=encrypt_text("Me senti acolhido"),
        what_learned=encrypt_text("Aprendi a observar meus gatilhos"),
        positive_point=encrypt_text("Consegui pedir ajuda"),
        resistance_or_disagreement=encrypt_text("Ainda tive resistencia"),
    )
    other_reflection = Reflection(
        client_id=other_user.id,
        therapist_id=therapist_user.id,
        feeling_after_session=encrypt_text("Outro sentimento"),
        what_learned=encrypt_text("Outro aprendizado"),
        positive_point=encrypt_text("Outro ponto"),
        resistance_or_disagreement=encrypt_text("Outra resistencia"),
    )
    db_session.add_all([my_reflection, other_reflection])
    db_session.flush()

    my_feedback = Feedback(
        reflection_id=my_reflection.id,
        ia_generated_content=encrypt_text("Seu progresso foi consistente"),
        ia_neuro_nutrition_tip=encrypt_text("Inclua omega 3"),
        ia_activity_suggestion=encrypt_text("Caminhada curta"),
        status="approved",
        approved_at=datetime.utcnow(),
    )
    other_feedback = Feedback(
        reflection_id=other_reflection.id,
        ia_generated_content=encrypt_text("Feedback de outro usuario"),
        ia_neuro_nutrition_tip=encrypt_text("Outra dica"),
        ia_activity_suggestion=encrypt_text("Outra atividade"),
        status="approved",
        approved_at=datetime.utcnow(),
    )
    db_session.add_all([my_feedback, other_feedback])

    my_dream = Dream(
        client_id=client_user.id,
        therapist_id=therapist_user.id,
        description=encrypt_text("Sonhei com uma ponte"),
        therapist_tags=encrypt_text("simbolismo"),
        therapist_notes=encrypt_text("Explorar transicoes"),
    )
    other_dream = Dream(
        client_id=other_user.id,
        therapist_id=therapist_user.id,
        description=encrypt_text("Sonho de outro usuario"),
        therapist_tags=encrypt_text("outro-tag"),
        therapist_notes=encrypt_text("outra-nota"),
    )
    db_session.add_all([my_dream, other_dream])
    db_session.commit()

    return {
        "consent": consent,
        "my_reflection": my_reflection,
        "other_reflection": other_reflection,
        "my_feedback": my_feedback,
        "other_feedback": other_feedback,
        "my_dream": my_dream,
        "other_dream": other_dream,
    }


def test_authenticated_user_exports_own_data(client, user_factory, auth_headers, db_session):
    therapist = user_factory(
        email="export-therapist@example.com",
        name="Therapist Export",
        role="therapist",
        password="StrongPass123",
    )
    client_user = user_factory(
        email="export-client@example.com",
        name="Cliente Exportacao",
        password="StrongPass123",
    )
    other_user = user_factory(
        email="export-other@example.com",
        name="Outro Usuario",
        password="StrongPass123",
    )
    rows = _seed_export_data(
        db_session,
        client_user=client_user,
        therapist_user=therapist,
        other_user=other_user,
    )

    response = client.get(
        "/me/export",
        headers={
            **auth_headers(client_user),
            "User-Agent": "pytest-data-export-agent",
            "X-Forwarded-For": "198.51.100.81",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="export.json"'

    body = response.json()
    assert body["profile"] == {
        "id": client_user.id,
        "email": "export-client@example.com",
        "name": "Cliente Exportacao",
        "role": "client",
        "is_active": True,
    }
    assert body["consents"] == [
        {
            "consent_version": None,
            "accepted_at": body["consents"][0]["accepted_at"],
        }
    ]
    assert body["reflections"] == [
        {
            "id": rows["my_reflection"].id,
            "feeling_after_session": "Me senti acolhido",
            "what_learned": "Aprendi a observar meus gatilhos",
            "positive_point": "Consegui pedir ajuda",
            "resistance_or_disagreement": "Ainda tive resistencia",
            "created_at": body["reflections"][0]["created_at"],
            "updated_at": body["reflections"][0]["updated_at"],
        }
    ]
    assert body["feedbacks"] == [
        {
            "id": rows["my_feedback"].id,
            "reflection_id": rows["my_reflection"].id,
            "ia_generated_content": "Seu progresso foi consistente",
            "ia_neuro_nutrition_tip": "Inclua omega 3",
            "ia_activity_suggestion": "Caminhada curta",
            "status": "approved",
            "approved_at": body["feedbacks"][0]["approved_at"],
            "created_at": body["feedbacks"][0]["created_at"],
        }
    ]
    assert body["dreams"] == [
        {
            "id": rows["my_dream"].id,
            "description": "Sonhei com uma ponte",
            "therapist_tags": "simbolismo",
            "therapist_notes": "Explorar transicoes",
            "created_at": body["dreams"][0]["created_at"],
            "updated_at": body["dreams"][0]["updated_at"],
        }
    ]


def test_export_without_token_returns_401(client):
    response = client.get("/me/export")

    assert response.status_code == 401


def test_export_omits_sensitive_fields(client, user_factory, auth_headers, db_session):
    therapist = user_factory(
        email="export-sensitive-therapist@example.com",
        name="Therapist Sensitive",
        role="therapist",
        password="StrongPass123",
    )
    client_user = user_factory(
        email="export-sensitive-client@example.com",
        name="Cliente Sensivel",
        password="StrongPass123",
    )
    other_user = user_factory(
        email="export-sensitive-other@example.com",
        name="Outro Sensivel",
        password="StrongPass123",
    )
    _seed_export_data(
        db_session,
        client_user=client_user,
        therapist_user=therapist,
        other_user=other_user,
    )

    response = client.get(
        "/me/export",
        headers=auth_headers(client_user),
    )

    assert response.status_code == 200

    raw_body = response.text
    for forbidden_key in [
        "password_hash",
        "email_hash",
        "email_encrypted",
        "name_encrypted",
        "audit_logs",
        "tokens",
    ]:
        assert forbidden_key not in raw_body


def test_export_does_not_return_other_users_data(client, user_factory, auth_headers, db_session):
    therapist = user_factory(
        email="export-isolation-therapist@example.com",
        name="Therapist Isolation",
        role="therapist",
        password="StrongPass123",
    )
    client_user = user_factory(
        email="export-isolation-client@example.com",
        name="Cliente Isolado",
        password="StrongPass123",
    )
    other_user = user_factory(
        email="export-isolation-other@example.com",
        name="Outro Isolado",
        password="StrongPass123",
    )
    rows = _seed_export_data(
        db_session,
        client_user=client_user,
        therapist_user=therapist,
        other_user=other_user,
    )

    response = client.get(
        "/me/export",
        headers=auth_headers(client_user),
    )

    assert response.status_code == 200

    body = response.json()
    assert {item["id"] for item in body["reflections"]} == {rows["my_reflection"].id}
    assert {item["id"] for item in body["feedbacks"]} == {rows["my_feedback"].id}
    assert {item["id"] for item in body["dreams"]} == {rows["my_dream"].id}
    assert other_user.email not in response.text
    assert other_user.name not in response.text
    assert "Outro sentimento" not in response.text
    assert "Feedback de outro usuario" not in response.text
    assert "Sonho de outro usuario" not in response.text


def test_data_export_request_is_audited(client, user_factory, auth_headers, db_session):
    therapist = user_factory(
        email="export-audit-therapist@example.com",
        name="Therapist Audit",
        role="therapist",
        password="StrongPass123",
    )
    client_user = user_factory(
        email="export-audit-client@example.com",
        name="Cliente Audit",
        password="StrongPass123",
    )
    other_user = user_factory(
        email="export-audit-other@example.com",
        name="Outro Audit",
        password="StrongPass123",
    )
    _seed_export_data(
        db_session,
        client_user=client_user,
        therapist_user=therapist,
        other_user=other_user,
    )

    response = client.get(
        "/me/export",
        headers={
            **auth_headers(client_user),
            "User-Agent": "pytest-export-audit-agent",
            "X-Forwarded-For": "198.51.100.82",
        },
    )

    assert response.status_code == 200

    rows = _load_audit_rows(db_session, "DATA_EXPORT_REQUEST")
    assert len(rows) == 1
    assert rows[0].user_id == client_user.id
    assert rows[0].resource_id == client_user.id
    assert rows[0].resource_type == "data_export"
    assert rows[0].ip_address == "198.51.100.82"
    assert rows[0].user_agent == "pytest-export-audit-agent"


def test_data_export_rate_limit_returns_429(client, user_factory, auth_headers):
    client_user = user_factory(
        email="export-rate-limit@example.com",
        name="Cliente Rate Limit",
        password="StrongPass123",
    )
    headers = {
        **auth_headers(client_user),
        "X-Forwarded-For": "198.51.100.83",
    }

    first = client.get("/me/export", headers=headers)
    second = client.get("/me/export", headers=headers)
    third = client.get("/me/export", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json() == {"detail": "Too many requests"}
