from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.modules.users.model import User
from utils.security import encrypt_value, hash_email, mask_email, normalize_email


def migrate_users(db: Session) -> tuple[int, int]:
    migrated = 0
    skipped = 0

    users = db.query(User).all()
    for user in users:
        legacy_email = (user.legacy_email or "").strip()
        legacy_name = (user.legacy_name or "").strip()

        if user.email_hash and user.email_encrypted and user.name_encrypted:
            skipped += 1
            continue

        if not legacy_email or not legacy_name:
            skipped += 1
            print(f"Skipping user id={user.id}: missing legacy data")
            continue

        normalized_email = normalize_email(legacy_email)
        user.email_hash = hash_email(normalized_email)
        user.email_encrypted = encrypt_value(normalized_email)
        user.name_encrypted = encrypt_value(legacy_name)

        migrated += 1
        print(f"Migrated user id={user.id} email={mask_email(normalized_email)}")

    db.commit()
    return migrated, skipped


def main() -> None:
    db = SessionLocal()
    try:
        migrated, skipped = migrate_users(db)
        print(f"Migration finished: migrated={migrated} skipped={skipped}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
