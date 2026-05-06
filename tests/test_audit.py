import json

from sqlalchemy.orm import Session

from app.modules.audit.model import AuditLog
from app.modules.audit.service import log_action, sanitize_audit_details
from app.modules.auth.service import login


def _load_single_audit_row(db_session, action: str | None = None) -> AuditLog:
    with Session(bind=db_session.get_bind()) as audit_session:
        query = audit_session.query(AuditLog)
        if action is not None:
            query = query.filter(AuditLog.action == action)
        return query.order_by(AuditLog.id.desc()).first()


def test_log_action_creates_audit_record(user_factory, db_session):
    user = user_factory(email="audit-create@example.com", password="StrongPass123")

    log_action(
        db_session,
        user_id=user.id,
        action="REFLECTION_CREATED",
        resource_type="reflection",
        resource_id=123,
        ip_address="203.0.113.10",
        user_agent="pytest-agent",
        details={"email": "audit-create@example.com", "content": "texto clinico"},
    )

    row = _load_single_audit_row(db_session)

    assert row.user_id == user.id
    assert row.action == "REFLECTION_CREATED"
    assert row.resource_type == "reflection"
    assert row.resource_id == 123
    assert row.ip_address == "203.0.113.10"
    assert row.user_agent == "pytest-agent"
    assert row.details is not None
    assert "audit-create@example.com" not in row.details
    assert "texto clinico" not in row.details


def test_sanitize_audit_details_removes_sensitive_fields():
    sanitized = sanitize_audit_details(
        {
            "email": "person@example.com",
            "name": "Maria Silva",
            "password": "secret",
            "content": "texto clinico",
            "nested": {
                "reflection": "conteudo sensivel",
                "token": "abc123",
                "notes": "fallback person@example.com",
            },
            "items": [
                {"anamnesis": "historia clinica"},
                "Bearer abc.def.ghi",
            ],
        }
    )

    assert sanitized["email"] == "[REDACTED]"
    assert sanitized["name"] == "[REDACTED]"
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["content"] == "[REDACTED]"
    assert sanitized["nested"]["reflection"] == "[REDACTED]"
    assert sanitized["nested"]["token"] == "[REDACTED]"
    assert sanitized["nested"]["notes"] == "fallback [REDACTED_EMAIL]"
    assert sanitized["items"][0]["anamnesis"] == "[REDACTED]"
    assert sanitized["items"][1] == "[REDACTED_TOKEN]"


def test_login_success_is_audited(client, user_factory, db_session):
    user = user_factory(email="login-success@example.com", password="StrongPass123")

    response = client.post(
        "/auth/login",
        json={"email": "login-success@example.com", "password": "StrongPass123"},
        headers={
            "User-Agent": "pytest-login-agent",
            "X-Forwarded-For": "198.51.100.24",
        },
    )

    assert response.status_code == 200

    row = _load_single_audit_row(db_session, "LOGIN_SUCCESS")
    details = json.loads(row.details or "{}")

    assert row.user_id == user.id
    assert row.resource_id == user.id
    assert row.ip_address == "198.51.100.24"
    assert row.user_agent == "pytest-login-agent"
    assert details == {"role": "client"}


def test_login_failed_is_audited(client, user_factory, db_session):
    user_factory(email="login-failed@example.com", password="StrongPass123")

    response = client.post(
        "/auth/login",
        json={"email": "login-failed@example.com", "password": "WrongPass123"},
        headers={
            "User-Agent": "pytest-failed-agent",
            "X-Forwarded-For": "198.51.100.33",
        },
    )

    assert response.status_code == 401

    row = _load_single_audit_row(db_session, "LOGIN_FAILED")
    assert row.user_id is None
    assert row.ip_address == "198.51.100.33"
    assert row.user_agent == "pytest-failed-agent"
    assert row.details is not None
    assert "login-failed@example.com" not in row.details
    assert "WrongPass123" not in row.details


def test_audit_logs_never_store_sensitive_values(user_factory, db_session):
    user = user_factory(email="sensitive@example.com", password="StrongPass123")

    log_action(
        db_session,
        user_id=user.id,
        action="PASSWORD_RESET_REQUEST",
        resource_type="auth",
        details={
            "email": "sensitive@example.com",
            "name": "Sensitive Person",
            "password": "StrongPass123",
            "access_token": "top-secret-token",
            "clinical_notes": "texto clinico privado",
            "free_text": "contact sensitive@example.com and use Bearer abc.def.ghi",
        },
    )

    row = _load_single_audit_row(db_session)

    assert "sensitive@example.com" not in row.details
    assert "Sensitive Person" not in row.details
    assert "StrongPass123" not in row.details
    assert "top-secret-token" not in row.details
    assert "texto clinico privado" not in row.details
    assert "[REDACTED_EMAIL]" in row.details
    assert "[REDACTED_TOKEN]" in row.details


def test_logger_failure_does_not_break_main_operation(user_factory, db_session, monkeypatch):
    user_factory(email="resilient@example.com", password="StrongPass123")

    def explode(*args, **kwargs):
        raise RuntimeError("audit failure")

    monkeypatch.setattr("app.modules.audit.service._persist_audit_log", explode)

    token = login(
        db_session,
        email="resilient@example.com",
        password="StrongPass123",
        ip_address="203.0.113.50",
        user_agent="pytest-agent",
    )

    assert token
    assert db_session.query(AuditLog).count() == 0
