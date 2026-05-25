from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
import pytest
from sqlalchemy.orm import Session

from app.config import JWT_ALGORITHM, JWT_SECRET
from app.core.security import create_access_token, decode_token
from app.modules.audit.model import AuditLog
from app.modules.auth.jwt_service import is_token_revoked, revoke_token
from app.modules.auth.model import RevokedToken


def _load_audit_actions(db_session, action: str) -> list[AuditLog]:
    with Session(bind=db_session.get_bind()) as audit_session:
        return audit_session.query(AuditLog).filter(AuditLog.action == action).all()


def test_create_access_token_includes_valid_jti(user_factory):
    user = user_factory(email="jti@example.com")
    token = create_access_token(subject=str(user.id))

    payload = decode_token(token)

    assert payload["sub"] == str(user.id)
    assert "exp" in payload
    assert "jti" in payload
    UUID(str(payload["jti"]))  # valida formato uuid


def test_legacy_tokens_without_jti_still_work_temporarily(client, legacy_user_factory):
    user = legacy_user_factory(email="legacy-token@example.com")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=30)).timestamp()),
    }
    legacy_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {legacy_token}"})
    assert response.status_code == 200
    assert response.json()["id"] == user.id


def test_revoke_token_persists_jti_and_is_token_revoked_reports_true(db_session, user_factory):
    user = user_factory(email="revoke@example.com")
    token = create_access_token(subject=str(user.id))
    payload = decode_token(token)
    jti = payload["jti"]

    assert is_token_revoked(db_session, jti) is False

    created = revoke_token(db_session, token_jti=jti, user_id=user.id)
    assert created is True

    assert is_token_revoked(db_session, jti) is True

    row = db_session.query(RevokedToken).filter(RevokedToken.token_jti == jti).one()
    assert row.user_id == user.id
    assert row.token_jti == jti
    assert row.token_jti != token  # segurança: nunca persistir JWT completo


def test_revoked_token_is_rejected_with_401_and_audited(client, db_session, user_factory):
    user = user_factory(email="reject@example.com")
    token = create_access_token(subject=str(user.id))
    payload = decode_token(token)
    jti = payload["jti"]

    revoke_token(db_session, token_jti=jti, user_id=user.id)

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Token inválido"

    actions = _load_audit_actions(db_session, "TOKEN_REJECTED_REVOKED")
    assert actions, "Deveria auditar TOKEN_REJECTED_REVOKED"
    assert "eyJ" not in (actions[-1].details or "")

