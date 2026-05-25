from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.modules.auth.jwt_service import delete_expired_revoked_tokens, is_token_revoked, revoke_token


def test_delete_expired_revoked_tokens_removes_only_expired_rows(db_session, user_factory):
    user = user_factory(email="cleanup@example.com")
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    expired_jti = "expired-jti"
    active_jti = "active-jti"

    revoke_token(db_session, token_jti=expired_jti, user_id=user.id, expires_at=now - timedelta(minutes=1))
    revoke_token(db_session, token_jti=active_jti, user_id=user.id, expires_at=now + timedelta(minutes=60))

    assert is_token_revoked(db_session, expired_jti) is True
    assert is_token_revoked(db_session, active_jti) is True

    deleted = delete_expired_revoked_tokens(db_session, now=datetime.now(timezone.utc))
    assert deleted == 1

    assert is_token_revoked(db_session, expired_jti) is False
    assert is_token_revoked(db_session, active_jti) is True

