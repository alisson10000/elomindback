from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.modules.feedback.model import Feedback
from app.modules.reflections.model import Reflection
from app.services.ia_service import generate_feedback_structured


def generate_for_reflection(db: Session, *, reflection_id: int) -> Feedback:
    """
    Gera feedback com IA para uma reflexão.
    Cria apenas um feedback por reflexão.
    """
    reflection = db.query(Reflection).filter(Reflection.id == reflection_id).first()
    if not reflection:
        raise HTTPException(status_code=404, detail="Reflection not found")

    # evita duplicar feedback para a mesma reflexão
    existing = db.query(Feedback).filter(Feedback.reflection_id == reflection_id).first()
    if existing:
        return existing

    # monta texto base para IA
    reflection_text = (
        f"Sentimento após sessão: {reflection.feeling_after_session}\n"
        f"O que aprendeu: {reflection.what_learned}\n"
        f"Ponto positivo: {reflection.positive_point}\n"
        f"Resistência: {reflection.resistance_or_disagreement or 'N/A'}\n"
    )

    # chama IA
    generated = generate_feedback_structured(reflection_text=reflection_text)

    fb = Feedback(
        reflection_id=reflection_id,
        ia_generated_content=generated["feedback"],
        ia_neuro_nutrition_tip=generated.get("neuro_tip"),
        ia_activity_suggestion=generated.get("activity"),
        status="pending_approval",
    )

    try:
        db.add(fb)
        db.commit()
        db.refresh(fb)
        return fb

    except IntegrityError:
        db.rollback()
        fb2 = db.query(Feedback).filter(Feedback.reflection_id == reflection_id).first()
        if fb2:
            return fb2
        raise


def list_pending(db: Session) -> list[Feedback]:
    """Lista feedbacks pendentes para aprovação do terapeuta"""
    return (
        db.query(Feedback)
        .filter(Feedback.status == "pending_approval")
        .order_by(Feedback.id.desc())
        .all()
    )


def approve(
    db: Session,
    *,
    feedback_id: int,
    therapist_id: int,
    update_data,
) -> Feedback:
    """Terapeuta aprova (e pode editar) o feedback da IA"""

    fb = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")

    if fb.status == "approved":
        return fb

    # terapeuta pode editar conteúdo antes de aprovar
    if update_data.ia_generated_content is not None:
        fb.ia_generated_content = update_data.ia_generated_content

    if update_data.ia_neuro_nutrition_tip is not None:
        fb.ia_neuro_nutrition_tip = update_data.ia_neuro_nutrition_tip

    if update_data.ia_activity_suggestion is not None:
        fb.ia_activity_suggestion = update_data.ia_activity_suggestion

    if update_data.therapist_notes is not None:
        fb.therapist_notes = update_data.therapist_notes

    fb.status = "approved"
    fb.therapist_approved_by = therapist_id
    fb.approved_at = datetime.utcnow()

    db.commit()
    db.refresh(fb)
    return fb


def reject(db: Session, *, feedback_id: int, therapist_id: int, notes: str | None) -> Feedback:
    """Terapeuta rejeita o feedback gerado pela IA"""

    fb = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")

    fb.status = "rejected"
    fb.therapist_approved_by = therapist_id
    fb.approved_at = None
    fb.therapist_notes = notes

    db.commit()
    db.refresh(fb)
    return fb


def get_by_reflection_for_client(db: Session, *, reflection_id: int, client_id: int) -> Feedback:
    """
    Cliente só pode ver feedback:
    - se a reflexão pertence a ele
    - e se status == approved
    """
    reflection = (
        db.query(Reflection)
        .filter(Reflection.id == reflection_id, Reflection.client_id == client_id)
        .first()
    )
    if not reflection:
        raise HTTPException(status_code=404, detail="Reflection not found for this user")

    fb = db.query(Feedback).filter(Feedback.reflection_id == reflection_id).first()
    if not fb or fb.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No approved feedback for this reflection",
        )

    return fb
