from __future__ import annotations

import asyncio
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_text, encrypt_text
from app.modules.anamnesis.model import Anamnesis
from app.modules.feedback.model import Feedback
from app.modules.push_tokens.service import get_user_push_tokens, send_expo_push
from app.modules.reflections.model import Reflection
from app.services.ia_service import generate_feedback_structured

STATUS_PENDING = "pending_approval"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"


# ======================
# Internal helpers
# ======================
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
    fb = (
        db.query(Feedback)
        .filter(Feedback.id == feedback_id)
        .one_or_none()
    )
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return fb


def _serialize_feedback(fb: Feedback) -> dict:
    return {
        "id": fb.id,
        "reflection_id": fb.reflection_id,
        "ia_generated_content": decrypt_text(fb.ia_generated_content),
        "ia_neuro_nutrition_tip": decrypt_text(fb.ia_neuro_nutrition_tip),
        "ia_activity_suggestion": decrypt_text(fb.ia_activity_suggestion),
        "status": fb.status,
        "therapist_approved_by": fb.therapist_approved_by,
        "therapist_notes": decrypt_text(fb.therapist_notes),
        "approved_at": fb.approved_at,
        "created_at": fb.created_at,
    }


def _parse_statuses(statuses: list[str] | None) -> list[str]:
    """
    Normaliza lista de statuses.
    Mantém compatível e evita lista vazia quebrando o IN().
    """
    if not statuses:
        return [STATUS_APPROVED, STATUS_REJECTED]

    cleaned = [s.strip() for s in statuses if s and s.strip()]
    return cleaned or [STATUS_APPROVED, STATUS_REJECTED]


def _get_anamnesis_summary_for_reflection(
    db: Session,
    reflection: Reflection,
) -> str | None:
    """
    Busca a anamnese (summary) para usar como contexto da IA.

    Resiliente:
    - se a Reflection não tiver therapist_id, retorna None
    - se não existir anamnese, retorna None
    """
    client_id = getattr(reflection, "client_id", None)
    therapist_id = getattr(reflection, "therapist_id", None)

    if not client_id or not therapist_id:
        print(
            f"ℹ️ [_get_anamnesis_summary_for_reflection] Sem contexto suficiente | "
            f"client_id={client_id} therapist_id={therapist_id}"
        )
        return None

    row = (
        db.query(Anamnesis)
        .filter(
            Anamnesis.client_id == client_id,
            Anamnesis.therapist_id == therapist_id,
        )
        .one_or_none()
    )

    if not row or not row.summary:
        print(
            f"ℹ️ [_get_anamnesis_summary_for_reflection] Anamnese não encontrada | "
            f"client_id={client_id} therapist_id={therapist_id}"
        )
        return None

    print(
        f"✅ [_get_anamnesis_summary_for_reflection] Anamnese encontrada | "
        f"client_id={client_id} therapist_id={therapist_id}"
    )
    return decrypt_text(row.summary)


def _notify_client_feedback_approved(
    db: Session,
    *,
    feedback: Feedback,
) -> None:
    """
    Envia push para o cliente dono da reflexão.
    Não quebra a aprovação se falhar.
    """
    print(
        f"🟡 [_notify_client_feedback_approved] Início | "
        f"feedback_id={feedback.id} reflection_id={feedback.reflection_id}"
    )

    try:
        reflection = (
            db.query(Reflection)
            .filter(Reflection.id == feedback.reflection_id)
            .one_or_none()
        )

        print(
            f"🔎 [_notify_client_feedback_approved] Reflection carregada | "
            f"found={bool(reflection)} reflection_id={feedback.reflection_id}"
        )

        if not reflection:
            print(
                f"⚠️ Reflection não encontrada para push | "
                f"feedback_id={feedback.id} reflection_id={feedback.reflection_id}"
            )
            return

        print(
            f"🧠 [_notify_client_feedback_approved] client_id da reflection: "
            f"{reflection.client_id} | feedback_id={feedback.id}"
        )

        if not reflection.client_id:
            print(
                f"⚠️ Reflection sem client_id para push | "
                f"feedback_id={feedback.id} reflection_id={feedback.reflection_id}"
            )
            return

        tokens = get_user_push_tokens(db, reflection.client_id)

        print(
            f"📲 [_notify_client_feedback_approved] tokens encontrados: {tokens} "
            f"| total={len(tokens) if tokens else 0} "
            f"| client_id={reflection.client_id}"
        )

        if not tokens:
            print(
                f"⚠️ Cliente sem push tokens | "
                f"client_id={reflection.client_id} feedback_id={feedback.id}"
            )
            return

        payload_data = {
            "type": "feedback_approved",
            "feedback_id": feedback.id,
            "reflection_id": feedback.reflection_id,
            "client_id": reflection.client_id,
        }

        print(
            f"📦 [_notify_client_feedback_approved] payload_data={payload_data}"
        )

        result = asyncio.run(
            send_expo_push(
                db=db,
                push_tokens=tokens,
                title="Sua devolutiva está pronta",
                body="Seu terapeuta aprovou uma nova devolutiva para sua reflexão.",
                data=payload_data,
            )
        )

        print(
            f"✅ Push enviada/processada | "
            f"client_id={reflection.client_id} "
            f"feedback_id={feedback.id} "
            f"reflection_id={feedback.reflection_id} "
            f"tokens={len(tokens)} "
            f"result={result}"
        )

    except Exception as e:
        print(f"⚠️ Falha ao enviar push do feedback {feedback.id}: {e}")


# ======================
# Public service methods
# ======================
def generate_for_reflection(db: Session, *, reflection_id: int) -> Feedback:
    """
    Gera feedback com IA para uma reflexão.
    Regra: cria apenas 1 feedback por reflexão (idempotente).

    Injeta anamnese (summary) como contexto da IA quando existir.
    """
    print(f"🟡 [generate_for_reflection] Início | reflection_id={reflection_id}")

    reflection = _get_reflection_or_404(db, reflection_id)

    existing = (
        db.query(Feedback)
        .filter(Feedback.reflection_id == reflection_id)
        .one_or_none()
    )
    if existing:
        print(
            f"ℹ️ [generate_for_reflection] Feedback já existia | "
            f"feedback_id={existing.id} reflection_id={reflection_id} status={existing.status}"
        )
        return _serialize_feedback(existing)

    reflection_text = (
        f"Sentimento apos sessao: {decrypt_text(reflection.feeling_after_session)}\n"
        f"O que aprendeu: {decrypt_text(reflection.what_learned)}\n"
        f"Ponto positivo: {decrypt_text(reflection.positive_point)}\n"
        f"Resistencia: {decrypt_text(reflection.resistance_or_disagreement) or 'N/A'}\n"
    )

    print(
        f"📝 [generate_for_reflection] Texto montado para IA | "
        f"reflection_id={reflection_id}"
    )

    anamnesis_summary = _get_anamnesis_summary_for_reflection(db, reflection)

    generated = generate_feedback_structured(
        reflection_text=reflection_text,
        anamnesis_summary=anamnesis_summary,
    )

    print(
        f"🤖 [generate_for_reflection] IA respondeu | "
        f"has_feedback={bool(generated.get('feedback'))} "
        f"has_neuro_tip={bool(generated.get('neuro_tip'))} "
        f"has_activity={bool(generated.get('activity'))}"
    )

    fb = Feedback(
        reflection_id=reflection_id,
        ia_generated_content=encrypt_text(generated.get("feedback")),
        ia_neuro_nutrition_tip=encrypt_text(generated.get("neuro_tip")),
        ia_activity_suggestion=encrypt_text(generated.get("activity")),
        status=STATUS_PENDING,
    )

    try:
        db.add(fb)
        db.commit()
        db.refresh(fb)

        print(
            f"✅ [generate_for_reflection] Feedback criado | "
            f"feedback_id={fb.id} reflection_id={fb.reflection_id} status={fb.status}"
        )
        return _serialize_feedback(fb)

    except IntegrityError:
        db.rollback()
        print(
            f"⚠️ [generate_for_reflection] IntegrityError; tentando recuperar feedback existente | "
            f"reflection_id={reflection_id}"
        )

        fb2 = (
            db.query(Feedback)
            .filter(Feedback.reflection_id == reflection_id)
            .one_or_none()
        )
        if fb2:
            print(
                f"✅ [generate_for_reflection] Feedback recuperado após rollback | "
                f"feedback_id={fb2.id} reflection_id={fb2.reflection_id}"
            )
            return _serialize_feedback(fb2)
        raise


def list_pending(db: Session) -> list[Feedback]:
    """Lista feedbacks pendentes para aprovação do terapeuta."""
    rows = (
        db.query(Feedback)
        .filter(Feedback.status == STATUS_PENDING)
        .order_by(Feedback.id.desc())
        .all()
    )

    print(f"📋 [list_pending] total={len(rows)}")
    return [_serialize_feedback(row) for row in rows]


def approve(
    db: Session,
    *,
    feedback_id: int,
    therapist_id: int,
    update_data,
) -> Feedback:
    """
    Terapeuta aprova (e pode editar) o feedback da IA.
    Após aprovar, envia push para o cliente dono da reflexão.
    """
    print(
        f"🟡 [approve] Início | feedback_id={feedback_id} therapist_id={therapist_id}"
    )

    fb = _get_feedback_or_404(db, feedback_id)

    print(
        f"📦 [approve] Feedback encontrado | "
        f"id={fb.id} reflection_id={fb.reflection_id} status_atual={fb.status}"
    )

    if fb.status == STATUS_APPROVED:
        print(f"ℹ️ [approve] Feedback já estava aprovado | feedback_id={fb.id}")
        return _serialize_feedback(fb)

    if getattr(update_data, "ia_generated_content", None) is not None:
        fb.ia_generated_content = encrypt_text(update_data.ia_generated_content)
        print(f"✏️ [approve] ia_generated_content atualizado | feedback_id={fb.id}")

    if getattr(update_data, "ia_neuro_nutrition_tip", None) is not None:
        fb.ia_neuro_nutrition_tip = encrypt_text(update_data.ia_neuro_nutrition_tip)
        print(f"✏️ [approve] ia_neuro_nutrition_tip atualizado | feedback_id={fb.id}")

    if getattr(update_data, "ia_activity_suggestion", None) is not None:
        fb.ia_activity_suggestion = encrypt_text(update_data.ia_activity_suggestion)
        print(f"✏️ [approve] ia_activity_suggestion atualizado | feedback_id={fb.id}")

    if getattr(update_data, "therapist_notes", None) is not None:
        fb.therapist_notes = encrypt_text(update_data.therapist_notes)
        print(f"✏️ [approve] therapist_notes atualizado | feedback_id={fb.id}")

    fb.status = STATUS_APPROVED
    fb.therapist_approved_by = therapist_id
    fb.approved_at = datetime.utcnow()

    print(
        f"💾 [approve] Salvando aprovação | "
        f"feedback_id={fb.id} novo_status={fb.status}"
    )

    db.commit()
    db.refresh(fb)

    print(
        f"✅ [approve] Feedback aprovado | "
        f"feedback_id={fb.id} reflection_id={fb.reflection_id} "
        f"approved_at={fb.approved_at}"
    )

    _notify_client_feedback_approved(db, feedback=fb)

    return _serialize_feedback(fb)


def reject(
    db: Session,
    *,
    feedback_id: int,
    therapist_id: int,
    notes: str | None,
) -> Feedback:
    """Terapeuta rejeita o feedback gerado pela IA."""
    print(
        f"🟡 [reject] Início | feedback_id={feedback_id} therapist_id={therapist_id}"
    )

    fb = _get_feedback_or_404(db, feedback_id)

    print(
        f"📦 [reject] Feedback encontrado | "
        f"id={fb.id} reflection_id={fb.reflection_id} status_atual={fb.status}"
    )

    fb.status = STATUS_REJECTED
    fb.therapist_approved_by = therapist_id
    fb.approved_at = None
    fb.therapist_notes = encrypt_text(notes)

    db.commit()
    db.refresh(fb)

    print(
        f"✅ [reject] Feedback rejeitado | "
        f"feedback_id={fb.id} reflection_id={fb.reflection_id}"
    )
    return _serialize_feedback(fb)


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
    print(
        f"🟡 [get_by_reflection_for_client] Início | "
        f"reflection_id={reflection_id} client_id={client_id}"
    )

    reflection = (
        db.query(Reflection)
        .filter(
            Reflection.id == reflection_id,
            Reflection.client_id == client_id,
        )
        .one_or_none()
    )
    if not reflection:
        print(
            f"❌ [get_by_reflection_for_client] Reflection não encontrada | "
            f"reflection_id={reflection_id} client_id={client_id}"
        )
        raise HTTPException(
            status_code=404,
            detail="Reflection not found for this user",
        )

    fb = (
        db.query(Feedback)
        .filter(Feedback.reflection_id == reflection_id)
        .one_or_none()
    )
    if not fb or fb.status != STATUS_APPROVED:
        print(
            f"❌ [get_by_reflection_for_client] Sem feedback aprovado | "
            f"reflection_id={reflection_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No approved feedback for this reflection",
        )

    print(
        f"✅ [get_by_reflection_for_client] Feedback aprovado encontrado | "
        f"feedback_id={fb.id} reflection_id={reflection_id}"
    )
    return _serialize_feedback(fb)


def get_by_reflection_for_therapist(
    db: Session,
    *,
    reflection_id: int,
) -> Feedback:
    """Terapeuta pode ver feedback da reflexão (qualquer status)."""
    print(f"🟡 [get_by_reflection_for_therapist] Início | reflection_id={reflection_id}")

    _get_reflection_or_404(db, reflection_id)

    fb = (
        db.query(Feedback)
        .filter(Feedback.reflection_id == reflection_id)
        .one_or_none()
    )
    if not fb:
        print(
            f"❌ [get_by_reflection_for_therapist] Feedback não encontrado | "
            f"reflection_id={reflection_id}"
        )
        raise HTTPException(
            status_code=404,
            detail="Feedback not found for this reflection",
        )

    print(
        f"✅ [get_by_reflection_for_therapist] Feedback encontrado | "
        f"feedback_id={fb.id} reflection_id={reflection_id} status={fb.status}"
    )
    return _serialize_feedback(fb)


def list_by_client_for_therapist(
    db: Session,
    *,
    client_id: int,
    statuses: list[str] | None = None,
) -> list[Feedback]:
    """
    Terapeuta lista feedbacks de um cliente (ex: approved + rejected).
    OBS: feedback não tem client_id direto; vem via Reflection.client_id.
    """
    statuses = _parse_statuses(statuses)

    rows = (
        db.query(Feedback)
        .join(Reflection, Reflection.id == Feedback.reflection_id)
        .filter(Reflection.client_id == client_id)
        .filter(Feedback.status.in_(statuses))
        .order_by(Feedback.id.desc())
        .all()
    )

    print(
        f"📋 [list_by_client_for_therapist] client_id={client_id} "
        f"statuses={statuses} total={len(rows)}"
    )
    return [_serialize_feedback(row) for row in rows]
