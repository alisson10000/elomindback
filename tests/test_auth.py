import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.modules.audit.model import AuditLog
from app.modules.auth.password_reset.service import (
    create_password_reset,
    reset_password_with_token,
)
from app.modules.auth.service import login, signup
from app.modules.users import service as user_service_module
from app.modules.users.service import get_user_by_email


def _load_single_audit_row(db_session, action: str) -> AuditLog:
    with Session(bind=db_session.get_bind()) as audit_session:
        return audit_session.query(AuditLog).filter(AuditLog.action == action).one()


def test_login_with_correct_email_works(user_factory, db_session, monkeypatch):
    user_factory(email="login@example.com", password="StrongPass123")
    observed = {}
    original_hash_email = user_service_module.hash_email

    def spy_hash_email(email: str) -> str:
        observed["email"] = email
        return original_hash_email(email)

    monkeypatch.setattr(user_service_module, "hash_email", spy_hash_email)

    token = login(db_session, email="login@example.com", password="StrongPass123")

    assert token
    assert observed["email"] == "login@example.com"


def test_login_with_wrong_email_fails(user_factory, db_session):
    user_factory(email="login@example.com", password="StrongPass123")

    with pytest.raises(HTTPException) as exc:
        login(db_session, email="wrong@example.com", password="StrongPass123")

    assert exc.value.status_code == 401


def test_signup_rejects_empty_name(db_session):
    with pytest.raises(HTTPException) as exc:
        signup(
            db_session,
            email="empty-name@example.com",
            name="",
            role="client",
            password="StrongPass123",
        )

    assert exc.value.status_code == 400


def test_signup_persists_only_encrypted_identity_fields(db_session):
    token = signup(
        db_session,
        email="signup@example.com",
        name="Signup User",
        role="therapist",
        password="StrongPass123",
    )

    user = get_user_by_email(db_session, "signup@example.com")

    assert token
    assert user is not None
    assert user.email_hash
    assert user.email_encrypted
    assert user.name_encrypted
    assert user.legacy_email in (None, "")
    assert user.legacy_name in (None, "")
    assert user.email == "signup@example.com"
    assert user.name == "Signup User"


def test_password_reset_works_for_encrypted_only_user_records(user_factory, db_session):
    user = user_factory(email="reset@example.com", password="OldPass123")

    token_plain, returned_user = create_password_reset(db_session, email="reset@example.com")
    reset_password_with_token(
        db_session,
        email="reset@example.com",
        token=token_plain,
        new_password="NewPass123",
    )
    db_session.refresh(user)

    assert returned_user.id == user.id
    assert user.legacy_email in (None, "")
    assert user.legacy_name in (None, "")
    assert verify_password("NewPass123", user.password_hash)


def test_login_rejects_null_like_inputs(db_session):
    with pytest.raises(HTTPException) as exc:
        login(db_session, email=None, password=None)

    assert exc.value.status_code == 400


def test_auth_endpoints_validate_invalid_and_missing_fields(client):
    invalid_email_signup = client.post(
        "/auth/signup",
        json={
            "email": "invalid-email",
            "name": "User",
            "password": "StrongPass123",
            "role": "client",
        },
    )
    empty_name_signup = client.post(
        "/auth/signup",
        json={
            "email": "valid@example.com",
            "name": "",
            "password": "StrongPass123",
            "role": "client",
        },
    )
    null_login = client.post(
        "/auth/login",
        json={"email": None, "password": None},
    )
    empty_email_login = client.post(
        "/auth/login",
        json={"email": "", "password": "StrongPass123"},
    )

    assert invalid_email_signup.status_code == 422
    assert empty_name_signup.status_code == 400
    assert null_login.status_code == 422
    assert empty_email_login.status_code == 422


def test_forgot_password_audits_request(client, user_factory, db_session):
    user = user_factory(email="forgot@example.com", password="StrongPass123")
    sent = {}

    def fake_send_email(*args, **kwargs):
        sent["called"] = True

    import app.modules.auth.password_reset.router as password_reset_router

    password_reset_router.send_email = fake_send_email

    response = client.post(
        "/auth/forgot-password",
        json={"email": "forgot@example.com"},
        headers={"User-Agent": "pytest-reset-agent", "X-Forwarded-For": "198.51.100.40"},
    )

    assert response.status_code == 200

    row = _load_single_audit_row(db_session, "PASSWORD_RESET_REQUEST")
    assert sent["called"] is True
    assert row.user_id == user.id
    assert row.ip_address == "198.51.100.40"
