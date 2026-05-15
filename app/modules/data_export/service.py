from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.crypto import decrypt_text
from app.modules.consents.model import Consent
from app.modules.dreams.model import Dream
from app.modules.feedback.model import Feedback
from app.modules.reflections.model import Reflection
from app.modules.users.model import User
from app.modules.users.service import serialize_user


def export_user_data(db: Session, *, user: User) -> dict:
    reflections = (
        db.query(Reflection)
        .filter(Reflection.client_id == user.id)
        .order_by(Reflection.created_at.asc(), Reflection.id.asc())
        .all()
    )

    feedbacks = (
        db.query(Feedback)
        .join(Reflection, Reflection.id == Feedback.reflection_id)
        .filter(Reflection.client_id == user.id)
        .order_by(Feedback.created_at.asc(), Feedback.id.asc())
        .all()
    )

    dreams = (
        db.query(Dream)
        .filter(Dream.client_id == user.id)
        .order_by(Dream.created_at.asc(), Dream.id.asc())
        .all()
    )

    consents = (
        db.query(Consent)
        .filter(Consent.client_id == user.id)
        .order_by(Consent.accepted_at.asc(), Consent.id.asc())
        .all()
    )

    return {
        "profile": serialize_user(user),
        "consents": [
            {
                "consent_version": None,
                "accepted_at": consent.accepted_at,
            }
            for consent in consents
        ],
        "reflections": [_serialize_reflection(row) for row in reflections],
        "feedbacks": [_serialize_feedback(row) for row in feedbacks],
        "dreams": [_serialize_dream(row) for row in dreams],
    }


def _serialize_reflection(reflection: Reflection) -> dict:
    return {
        "id": reflection.id,
        "feeling_after_session": decrypt_text(reflection.feeling_after_session),
        "what_learned": decrypt_text(reflection.what_learned),
        "positive_point": decrypt_text(reflection.positive_point),
        "resistance_or_disagreement": decrypt_text(reflection.resistance_or_disagreement),
        "created_at": reflection.created_at,
        "updated_at": reflection.updated_at,
    }


def _serialize_feedback(feedback: Feedback) -> dict:
    return {
        "id": feedback.id,
        "reflection_id": feedback.reflection_id,
        "ia_generated_content": decrypt_text(feedback.ia_generated_content),
        "ia_neuro_nutrition_tip": decrypt_text(feedback.ia_neuro_nutrition_tip),
        "ia_activity_suggestion": decrypt_text(feedback.ia_activity_suggestion),
        "status": feedback.status,
        "approved_at": feedback.approved_at,
        "created_at": feedback.created_at,
    }


def _serialize_dream(dream: Dream) -> dict:
    return {
        "id": dream.id,
        "description": decrypt_text(dream.description),
        "therapist_tags": decrypt_text(dream.therapist_tags),
        "therapist_notes": decrypt_text(dream.therapist_notes),
        "created_at": dream.created_at,
        "updated_at": dream.updated_at,
    }
