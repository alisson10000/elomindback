from __future__ import annotations

from app.db.session import SessionLocal
from app.modules.auth.jwt_service import delete_expired_revoked_tokens


def main() -> int:
    db = SessionLocal()
    try:
        deleted = delete_expired_revoked_tokens(db)
    finally:
        db.close()

    print(f"deleted={deleted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

