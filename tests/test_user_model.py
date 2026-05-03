from app.core.security import hash_password
from app.modules.users.service import create_user, get_user_by_email, serialize_user


def test_create_user_persists_only_sensitive_fields_encrypted(db_session):
    email = "user@example.com"
    name = "Sensitive User"

    user = create_user(
        db_session,
        email=email,
        name=name,
        role="client",
        password_hash=hash_password("StrongPass123"),
    )

    stored = get_user_by_email(db_session, email)

    assert stored is not None
    assert stored.email_hash
    assert stored.email_encrypted
    assert stored.name_encrypted
    assert stored.email_encrypted != email
    assert stored.name_encrypted != name
    assert stored.legacy_email in (None, "")
    assert stored.legacy_name in (None, "")
    assert stored.email == email
    assert stored.name == name
    assert stored.id == user.id


def test_serialize_user_returns_frontend_safe_shape(user_factory):
    user = user_factory(email="frontend@example.com", name="Frontend User", role="therapist")

    payload = serialize_user(user)

    assert payload == {
        "id": user.id,
        "email": "frontend@example.com",
        "name": "Frontend User",
        "role": "therapist",
        "is_active": True,
    }
