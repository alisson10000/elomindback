from __future__ import annotations

from app.core.crypto import decrypt_text, encrypt_text
from app.modules.feedback import service as feedback_service
from app.modules.feedback.model import Feedback
from app.modules.reflections.model import Reflection


def test_generate_for_reflection_saves_encrypted_feedback_fields(db_session, user_factory, monkeypatch):
    client_user = user_factory(
        email="feedback-client@example.com",
        name="Feedback Client",
        role="client",
    )
    therapist_user = user_factory(
        email="feedback-therapist@example.com",
        name="Feedback Therapist",
        role="therapist",
    )

    reflection = Reflection(
        client_id=client_user.id,
        therapist_id=therapist_user.id,
        feeling_after_session=encrypt_text("Saí da sessão ansiosa."),
        what_learned=encrypt_text("Percebi o peso do trabalho e da autocobrança."),
        positive_point=encrypt_text("Consegui pedir ajuda."),
        resistance_or_disagreement=encrypt_text("Ainda sinto resistência em desacelerar."),
    )
    db_session.add(reflection)
    db_session.commit()
    db_session.refresh(reflection)

    monkeypatch.setattr(
        feedback_service,
        "generate_feedback_structured",
        lambda **kwargs: {
            "feedback": "Você citou trabalho e autocobrança, e também reconheceu que conseguiu pedir ajuda. O que merece mais atenção nos próximos dias?",
            "neuro_tip": "Manter água por perto e incluir frutas e aveia ao longo do dia pode apoiar a microbiota.",
            "activity": "Faça uma caminhada leve de 10 minutos e alongue os ombros depois.",
        },
    )

    result = feedback_service.generate_for_reflection(
        db_session,
        reflection_id=reflection.id,
    )

    stored = db_session.query(Feedback).filter(Feedback.reflection_id == reflection.id).one()

    assert stored.ia_generated_content != result["ia_generated_content"]
    assert stored.ia_neuro_nutrition_tip != result["ia_neuro_nutrition_tip"]
    assert stored.ia_activity_suggestion != result["ia_activity_suggestion"]
    assert decrypt_text(stored.ia_generated_content) == result["ia_generated_content"]
    assert decrypt_text(stored.ia_neuro_nutrition_tip) == result["ia_neuro_nutrition_tip"]
    assert decrypt_text(stored.ia_activity_suggestion) == result["ia_activity_suggestion"]


def test_get_by_reflection_for_therapist_returns_decrypted_fields(db_session, user_factory):
    client_user = user_factory(
        email="decrypt-client@example.com",
        name="Decrypt Client",
        role="client",
    )
    therapist_user = user_factory(
        email="decrypt-therapist@example.com",
        name="Decrypt Therapist",
        role="therapist",
    )

    reflection = Reflection(
        client_id=client_user.id,
        therapist_id=therapist_user.id,
        feeling_after_session=encrypt_text("Saí mais cansada."),
        what_learned=encrypt_text("Preciso pausar mais no trabalho."),
        positive_point=encrypt_text("Consegui perceber meu limite."),
        resistance_or_disagreement=None,
    )
    db_session.add(reflection)
    db_session.commit()
    db_session.refresh(reflection)

    feedback = Feedback(
        reflection_id=reflection.id,
        ia_generated_content=encrypt_text("Feedback terapêutico aprovado."),
        ia_neuro_nutrition_tip=encrypt_text("Beba água e inclua legumes no dia a dia."),
        ia_activity_suggestion=encrypt_text("Faça uma caminhada curta e alongue as costas."),
        status=feedback_service.STATUS_APPROVED,
        therapist_approved_by=therapist_user.id,
    )
    db_session.add(feedback)
    db_session.commit()

    result = feedback_service.get_by_reflection_for_therapist(
        db_session,
        reflection_id=reflection.id,
    )

    assert result["ia_generated_content"] == "Feedback terapêutico aprovado."
    assert result["ia_neuro_nutrition_tip"] == "Beba água e inclua legumes no dia a dia."
    assert result["ia_activity_suggestion"] == "Faça uma caminhada curta e alongue as costas."
