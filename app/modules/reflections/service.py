from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import or_, func, and_

from app.modules.reflections.model import Reflection
from app.modules.feedback.model import Feedback
from app.modules.users.model import User


# -------------------------
# CLIENT
# -------------------------
def create_reflection(db: Session, client_id: int, data):
    ref = Reflection(
        client_id=client_id,
        feeling_after_session=data.feeling_after_session,
        what_learned=data.what_learned,
        positive_point=data.positive_point,
        resistance_or_disagreement=getattr(data, "resistance_or_disagreement", None),
    )
    db.add(ref)
    db.commit()
    db.refresh(ref)
    return ref  # bate com ReflectionOut via from_attributes


def list_my_reflections_with_delete_flag(db: Session, client_id: int):
    # existe feedback aprovado por reflection?
    approved_sq = (
        db.query(
            Feedback.reflection_id.label("rid"),
            func.max(Feedback.created_at).label("last_approved_at"),
        )
        .filter(Feedback.status == "approved")
        .group_by(Feedback.reflection_id)
        .subquery()
    )

    q = (
        db.query(Reflection, approved_sq.c.last_approved_at)
        .outerjoin(approved_sq, approved_sq.c.rid == Reflection.id)
        .filter(Reflection.client_id == client_id)
        .order_by(Reflection.created_at.desc())
    )

    items = []
    for ref, last_approved_at in q.all():
        items.append(
            {
                "id": ref.id,
                "client_id": ref.client_id,
                "feeling_after_session": ref.feeling_after_session,
                "what_learned": ref.what_learned,
                "positive_point": ref.positive_point,
                "resistance_or_disagreement": ref.resistance_or_disagreement,
                "created_at": ref.created_at,
                "can_delete": last_approved_at is None,
            }
        )
    return items


def delete_reflection(db: Session, reflection_id: int, client_id: int):
    ref = (
        db.query(Reflection)
        .filter(Reflection.id == reflection_id, Reflection.client_id == client_id)
        .first()
    )
    if not ref:
        return False

    approved_exists = (
        db.query(Feedback.id)
        .filter(Feedback.reflection_id == reflection_id, Feedback.status == "approved")
        .first()
        is not None
    )
    if approved_exists:
        raise ValueError("Não é possível excluir: já existe feedback aprovado.")

    db.delete(ref)
    db.commit()
    return True


# -------------------------
# THERAPIST
# -------------------------
def get_reflection_detail_for_therapist(db: Session, reflection_id: int):
    row = (
        db.query(Reflection, User.name)
        .join(User, User.id == Reflection.client_id)
        .filter(Reflection.id == reflection_id)
        .first()
    )
    if not row:
        return None

    ref, client_name = row

    # retorno em dict bate com ReflectionDetailOut
    return {
        "id": ref.id,
        "client_id": ref.client_id,
        "client_name": client_name,
        "feeling_after_session": ref.feeling_after_session,
        "what_learned": ref.what_learned,
        "positive_point": ref.positive_point,
        "resistance_or_disagreement": ref.resistance_or_disagreement,
        "created_at": ref.created_at,
    }


def list_pending_reflections(db: Session):
    """
    Pendentes = reflection sem feedback aprovado.
    Evita duplicar quando existe mais de um feedback por reflection
    pegando apenas o ÚLTIMO feedback (por created_at).
    """

    last_fb_sq = (
        db.query(
            Feedback.reflection_id.label("rid"),
            func.max(Feedback.created_at).label("last_created_at"),
        )
        .group_by(Feedback.reflection_id)
        .subquery()
    )

    q = (
        db.query(Reflection, User.name, Feedback.status)
        .join(User, User.id == Reflection.client_id)
        .outerjoin(last_fb_sq, last_fb_sq.c.rid == Reflection.id)
        .outerjoin(
            Feedback,
            and_(
                Feedback.reflection_id == Reflection.id,
                Feedback.created_at == last_fb_sq.c.last_created_at,
            ),
        )
        .filter(or_(Feedback.id.is_(None), Feedback.status != "approved"))
        .order_by(Reflection.created_at.desc())
    )

    items = []
    for ref, client_name, fb_status in q.all():
        items.append(
            {
                "id": ref.id,
                "client_id": ref.client_id,
                "client_name": client_name,
                "feeling_after_session": ref.feeling_after_session,
                "created_at": ref.created_at,
                # (não entra no schema, então não devolvo aqui)
            }
        )
    return items
