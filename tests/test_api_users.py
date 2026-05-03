import hashlib
import re


SHA256_HEX_RE = re.compile(r"\b[a-f0-9]{64}\b")


def test_auth_me_returns_frontend_compatible_safe_payload(client, user_factory, auth_headers):
    user = user_factory(email="api@example.com", name="API User", role="client")

    response = client.get("/auth/me", headers=auth_headers(user))

    assert response.status_code == 200
    assert response.json() == {
        "id": user.id,
        "email": "api@example.com",
        "name": "API User",
        "role": "client",
    }


def test_users_clients_response_is_decrypted_and_does_not_leak_sensitive_fields(
    client,
    user_factory,
    auth_headers,
):
    therapist = user_factory(email="therapist@example.com", name="Therapist", role="therapist")
    client_user = user_factory(email="listed@example.com", name="Listed User", role="client")

    response = client.get("/users/clients", headers=auth_headers(therapist))

    assert response.status_code == 200
    payload = response.json()
    assert payload == [
        {
            "id": client_user.id,
            "email": "listed@example.com",
            "name": "Listed User",
            "role": "client",
            "is_active": True,
        }
    ]

    raw_body = response.text
    assert "email_encrypted" not in raw_body
    assert "name_encrypted" not in raw_body
    assert "email_hash" not in raw_body
    assert client_user.email_encrypted not in raw_body
    assert client_user.name_encrypted not in raw_body
    assert client_user.email_hash not in raw_body
    assert "gAAAAA" not in raw_body
    assert not SHA256_HEX_RE.search(raw_body)


def test_auth_me_response_does_not_expose_ciphertext_or_hashes(client, user_factory, auth_headers):
    user = user_factory(email="no-leak@example.com", name="No Leak", role="client")

    response = client.get("/auth/me", headers=auth_headers(user))
    raw_body = response.text

    assert response.status_code == 200
    assert user.email_encrypted not in raw_body
    assert user.name_encrypted not in raw_body
    assert user.email_hash not in raw_body
    assert "gAAAAA" not in raw_body
    assert hashlib.sha256(user.email.encode("utf-8")).hexdigest() not in raw_body
