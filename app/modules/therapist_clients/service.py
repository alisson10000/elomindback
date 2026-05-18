from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.modules.therapist_clients.model import TherapistClient

THERAPIST_CLIENT_STATUS_ACTIVE = "active"
THERAPIST_CLIENT_STATUS_ENDED = "ended"

_THERAPIST_CLIENT_INDEX_DEFINITIONS = {
    "ix_therapist_clients_status": "CREATE INDEX ix_therapist_clients_status ON therapist_clients (status)",
    "ix_therapist_clients_ended_at": "CREATE INDEX ix_therapist_clients_ended_at ON therapist_clients (ended_at)",
    "ix_therapist_clients_client_status": (
        "CREATE INDEX ix_therapist_clients_client_status ON therapist_clients (client_id, status)"
    ),
}


def ensure_therapist_client_retention_schema(bind: Engine) -> None:
    inspector = inspect(bind)
    if "therapist_clients" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("therapist_clients")}

    with bind.begin() as connection:
        if "status" not in existing_columns:
            connection.exec_driver_sql(
                "ALTER TABLE therapist_clients "
                "ADD COLUMN status VARCHAR(30) NOT NULL DEFAULT 'active'"
            )
        if "ended_at" not in existing_columns:
            connection.exec_driver_sql(
                "ALTER TABLE therapist_clients "
                "ADD COLUMN ended_at DATETIME NULL"
            )

    refreshed_inspector = inspect(bind)
    existing_indexes = {index["name"] for index in refreshed_inspector.get_indexes("therapist_clients")}

    with bind.begin() as connection:
        for index_name, ddl in _THERAPIST_CLIENT_INDEX_DEFINITIONS.items():
            if index_name not in existing_indexes:
                connection.exec_driver_sql(ddl)


def link_therapist_client(
    db: Session,
    *,
    therapist_id: int,
    client_id: int
) -> TherapistClient:
    link = TherapistClient(
        therapist_id=therapist_id,
        client_id=client_id,
        status=THERAPIST_CLIENT_STATUS_ACTIVE,
        ended_at=None,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link
