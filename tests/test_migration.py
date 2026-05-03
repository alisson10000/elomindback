from scripts.migrate_users_encryption import migrate_users
from utils.security import mask_email


def test_migration_populates_encrypted_fields_without_corrupting_legacy_data(
    db_session,
    legacy_user_factory,
):
    user = legacy_user_factory(email="legacy@example.com", name="Legacy Name")

    migrated, skipped = migrate_users(db_session)
    db_session.refresh(user)

    assert migrated == 1
    assert skipped == 0
    assert user.email_hash
    assert user.email_encrypted
    assert user.name_encrypted
    assert user.email == "legacy@example.com"
    assert user.name == "Legacy Name"
    assert user.email_encrypted != "legacy@example.com"
    assert user.name_encrypted != "Legacy Name"


def test_migration_logs_masked_email_without_sensitive_plaintext(
    db_session,
    legacy_user_factory,
    capsys,
):
    legacy_user_factory(email="masked@example.com", name="Hidden Name")

    migrate_users(db_session)
    captured = capsys.readouterr()

    assert mask_email("masked@example.com") in captured.out
    assert "masked@example.com" not in captured.out
    assert "Hidden Name" not in captured.out
