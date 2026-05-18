from __future__ import annotations

import argparse
import json

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.modules.data_retention.service import delete_expired_data
from app.modules.therapist_clients.service import ensure_therapist_client_retention_schema


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete expired EloMind data according to retention policy.")
    parser.add_argument("--dry-run", action="store_true", help="Report counts without deleting rows.")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    ensure_therapist_client_retention_schema(engine)

    db = SessionLocal()
    try:
        summary = delete_expired_data(db, dry_run=args.dry_run)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    finally:
        db.close()


if __name__ == "__main__":
    main()
