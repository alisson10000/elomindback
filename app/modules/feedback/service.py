from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.modules.feedback.model import Feedback
from app.modules.reflections.model import Reflection
from app.services.ia_service import generate_feedback_structured

STATUS_PENDING = "pending_approval"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"


def _get_reflection_or_404(db: Session, reflection_id: int) -> Reflection:
    reflection = (
        db.query(Reflection)
        .filter(Reflection.id == reflection_id)
        .one_or_none()
    )
    if not reflection:
        raise HTTPException(status_code=404, detail="Reflection not found")
    return reflection


def _get_feedback_or_404(db: Session, feedback_id: int) -> Feedback:
    fb = db.query(Feedback).filter(Feedback.id == feedback_id).one_or_none()
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return fb


def generate_for_reflection(db: Session, *, reflection_id: int) -> Feedback:
    """
    Gera feedback com IA para uma reflexão.
    Regra: cria apenas 1 feedback por reflexão (idempotente).
    """
    reflection = _get_reflection_or_404(db, reflection_id)

    existing = (
        db.query(Feedback)
        .filter(Feedback.reflection_id == reflection_id)
        .one_or_none()
    )
    if existing:
        return existing

    reflection_text = (
        f"Sentimento após sessão: {reflection.feeling_after_session}\n"
        f"O que aprendeu: {reflection.what_learned}\n"
        f"Ponto positivo: {reflection.positive_point}\n"
        f"Resistência: {reflection.resistance_or_disagreement or 'N/A'}\n"
    )

    generated = generate_feedback_structured(reflection_text=reflection_text)

    fb = Feedback(
        reflection_id=reflection_id,
        ia_generated_content=generated.get("feedback"),
        ia_neuro_nutrition_tip=generated.get("neuro_tip"),
        ia_activity_suggestion=generated.get("activity"),
        status=STATUS_PENDING,
    )

    try:
        db.add(fb)
        db.commit()
        db.refresh(fb)
        return fb
    except IntegrityError:
        # Em concorrência, pode criar ao mesmo tempo. Rebusca.
        db.rollback()
        fb2 = (
            db.query(Feedback)
            .filter(Feedback.reflection_id == reflection_id)
            .one_or_none()
        )
        if fb2:
            return fb2
        raise


def list_pending(db: Session) -> list[Feedback]:
    """Lista feedbacks pendentes para aprovação do terapeuta"""
    return (
        db.query(Feedback)
        .filter(Feedback.status == STATUS_PENDING)
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
    fb = _get_feedback_or_404(db, feedback_id)

    if fb.status == STATUS_APPROVED:
        return fb

    # terapeuta pode editar conteúdo antes de aprovar
    if getattr(update_data, "ia_generated_content", None) is not None:
        fb.ia_generated_content = update_data.ia_generated_content

    if getattr(update_data, "ia_neuro_nutrition_tip", None) is not None:
        fb.ia_neuro_nutrition_tip = update_data.ia_neuro_nutrition_tip

    if getattr(update_data, "ia_activity_suggestion", None) is not None:
        fb.ia_activity_suggestion = update_data.ia_activity_suggestion

    if getattr(update_data, "therapist_notes", None) is not None:
        fb.therapist_notes = update_data.therapist_notes

    fb.status = STATUS_APPROVED
    fb.therapist_approved_by = therapist_id
    fb.approved_at = datetime.utcnow()

    db.commit()
    db.refresh(fb)
    return fb


def reject(
    db: Session,
    *,
    feedback_id: int,
    therapist_id: int,
    notes: str | None,
) -> Feedback:
    """Terapeuta rejeita o feedback gerado pela IA"""
    fb = _get_feedback_or_404(db, feedback_id)

    fb.status = STATUS_REJECTED
    fb.therapist_approved_by = therapist_id
    fb.approved_at = None
    fb.therapist_notes = notes

    db.commit()
    db.refresh(fb)
    return fb


def get_by_reflection_for_client(
    db: Session,
    *,
    reflection_id: int,
    client_id: int,
) -> Feedback:
    """
    Cliente só pode ver feedback:
    - se a reflexão pertence a ele
    - e se status == approved
    """
    reflection = (
        db.query(Reflection)
        .filter(Reflection.id == reflection_id, Reflection.client_id == client_id)
        .one_or_none()
    )
    if not reflection:
        raise HTTPException(status_code=404, detail="Reflection not found for this user")

    fb = (
        db.query(Feedback)
        .filter(Feedback.reflection_id == reflection_id)
        .one_or_none()
    )
    if not fb or fb.status != STATUS_APPROVED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No approved feedback for this reflection",
        )

    return fb


def get_by_reflection_for_therapist(
    db: Session,
    *,
    reflection_id: int,
) -> Feedback:
    """
    ✅ NOVO: terapeuta pode ver feedback da reflexão (qualquer status).
    Isso resolve o app não conseguir carregar o feedback diretamente.
    """
    _get_reflection_or_404(db, reflection_id)

    fb = (
        db.query(Feedback)
        .filter(Feedback.reflection_id == reflection_id)
        .one_or_none()
    )
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found for this reflection")

    return fb
