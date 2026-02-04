from sqlalchemy.orm import Session
from app.modules.therapist_clients.model import TherapistClient


def link_therapist_client(
    db: Session,
    *,
    therapist_id: int,
    client_id: int
) -> TherapistClient:
    link = TherapistClient(
        therapist_id=therapist_id,
        client_id=client_id
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link
