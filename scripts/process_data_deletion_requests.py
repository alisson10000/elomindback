from __future__ import annotations

import argparse
import json

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.modules.data_deletion_requests.service import (
    ensure_data_deletion_request_schema,
    process_due_deletion_requests,
)
from app.modules.therapist_clients.service import ensure_therapist_client_retention_schema


def main() -> None:
    parser = argparse.ArgumentParser(description="Process due LGPD hard-delete requests.")
    parser.add_argument("--dry-run", action="store_true", help="Only report how many requests are due.")
    parser.add_argument("--limit", type=int, default=None, help="Process at most this many due requests.")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    ensure_data_deletion_request_schema(engine)
    ensure_therapist_client_retention_schema(engine)

    db = SessionLocal()
    try:
        summary = process_due_deletion_requests(db, dry_run=args.dry_run, limit=args.limit)
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    finally:
        db.close()


if __name__ == "__main__":
    main()
