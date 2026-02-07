from sqlalchemy.orm import Session
from app.modules.consents.model import Consent


def get_consent_by_client_id(db: Session, client_id: int) -> Consent | None:
    return db.query(Consent).filter(Consent.client_id == client_id).first()


def accept_consent(db: Session, *, client_id: int) -> Consent:
    consent = get_consent_by_client_id(db, client_id)
    if consent:
        return consent

    consent = Consent(client_id=client_id)
    db.add(consent)
    db.commit()
    db.refresh(consent)
    return consent
