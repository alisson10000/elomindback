from sqlalchemy.orm import Session
from app.modules.reflections.model import Reflection

def create_reflection(db: Session, *, client_id: int, data) -> Reflection:
    ref = Reflection(client_id=client_id, **data.model_dump())
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref

def list_my_reflections(db: Session, *, client_id: int) -> list[Reflection]:
    return db.query(Reflection).filter(Reflection.client_id == client_id).order_by(Reflection.id.desc()).all()
