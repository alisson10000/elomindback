from sqlalchemy.orm import Session

from app.modules.audit.service import log_action
from app.modules.consents.model import Consent


def get_consent_by_client_id(db: Session, client_id: int) -> Consent | None:
    return db.query(Consent).filter(Consent.client_id == client_id).first()


def accept_consent(
    db: Session,
    *,
    client_id: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> Consent:
    consent = get_consent_by_client_id(db, client_id)
    if consent:
        return consent

    consent = Consent(client_id=client_id)
    db.add(consent)
    db.commit()
    db.refresh(consent)
    log_action(
        db,
        user_id=client_id,
        action="CONSENT_ACCEPTED",
        resource_type="consent",
        resource_id=consent.id,
        ip_address=ip_address,
        user_agent=user_agent,
        details={"client_id": client_id},
    )
    return consent
