from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.audit.model import AuditLog


def _load_audit_actions(db_session, action: str) -> list[AuditLog]:
    with Session(bind=db_session.get_bind()) as audit_session:
        return audit_session.query(AuditLog).filter(AuditLog.action == action).all()


def test_logout_revokes_current_token_and_registers_audit(client, user_factory, auth_headers, db_session):
    user = user_factory(email="logout@example.com")
    headers = auth_headers(user)

    me_before = client.get("/auth/me", headers=headers)
    assert me_before.status_code == 200

    logout = client.post(
        "/auth/logout",
        headers={**headers, "User-Agent": "pytest-agent", "X-Forwarded-For": "203.0.113.10"},
    )
    assert logout.status_code == 200
    assert logout.json() == {"ok": True}

    me_after = client.get("/auth/me", headers=headers)
    assert me_after.status_code == 401
    assert me_after.json()["detail"] == "Token inválido"

    assert _load_audit_actions(db_session, "LOGOUT")
    assert _load_audit_actions(db_session, "TOKEN_REVOKED")
    assert _load_audit_actions(db_session, "TOKEN_REJECTED_REVOKED")

