from __future__ import annotations

import asyncio

from sqlalchemy.orm import Session
from sqlalchemy import or_, func, and_

from app.modules.reflections.model import Reflection
from app.modules.feedback.model import Feedback
from app.modules.users.model import User
from app.modules.therapist_clients.model import TherapistClient
from app.modules.push_tokens.service import get_user_push_tokens, send_expo_push


# -------------------------
# HELPERS
# -------------------------
def get_therapist_by_client_id(db: Session, client_id: int):
    print(f"🔎 [get_therapist_by_client_id] Buscando terapeuta do client_id={client_id}")

    therapist = (
        db.query(User)
        .join(TherapistClient, TherapistClient.therapist_id == User.id)
        .filter(
            TherapistClient.client_id == client_id,
            User.role == "therapist",
        )
        .first()
    )

    if therapist:
        print(
            f"✅ [get_therapist_by_client_id] Terapeuta encontrado: "
            f"id={therapist.id} nome={getattr(therapist, 'name', None)}"
        )
    else:
        print(f"⚠️ [get_therapist_by_client_id] Nenhum terapeuta encontrado para client_id={client_id}")

    return therapist


# -------------------------
# CLIENT
# -------------------------
def create_reflection(db: Session, client_id: int, data):
    print("\n" + "=" * 80)
    print(f"🟡 [create_reflection] Iniciando criação de reflexão | client_id={client_id}")
    print(
        f"📦 [create_reflection] Payload recebido: "
        f"feeling_after_session={getattr(data, 'feeling_after_session', None)!r}, "
        f"what_learned={getattr(data, 'what_learned', None)!r}, "
        f"positive_point={getattr(data, 'positive_point', None)!r}, "
        f"resistance_or_disagreement={getattr(data, 'resistance_or_disagreement', None)!r}"
    )

    therapist = get_therapist_by_client_id(db, client_id)

    ref = Reflection(
        client_id=client_id,
        therapist_id=therapist.id if therapist else None,
        feeling_after_session=data.feeling_after_session,
        what_learned=data.what_learned,
        positive_point=data.positive_point,
        resistance_or_disagreement=getattr(data, "resistance_or_disagreement", None),
    )

    print(
        f"📝 [create_reflection] Reflection montada: "
        f"client_id={ref.client_id}, therapist_id={ref.therapist_id}"
    )

    db.add(ref)
    print("💾 [create_reflection] Salvando reflexão no banco...")
    db.commit()
    db.refresh(ref)

    print(
        f"✅ [create_reflection] Reflexão criada com sucesso | "
        f"id={ref.id} created_at={ref.created_at} therapist_id={ref.therapist_id}"
    )

    # Notificação para o terapeuta quando o cliente cria uma nova reflexão
    if therapist:
        print(f"🔔 [create_reflection] Terapeuta existe, iniciando busca de push tokens | therapist_id={therapist.id}")

        tokens = get_user_push_tokens(db, therapist.id)
        print(f"📱 [create_reflection] Tokens encontrados para therapist_id={therapist.id}: {tokens}")

        if tokens:
            try:
                print(
                    f"📤 [create_reflection] Enviando push da reflexão id={ref.id} "
                    f"para therapist_id={therapist.id}"
                )

                asyncio.run(
                    send_expo_push(
                        db=db,
                        push_tokens=tokens,
                        title="Nova reflexão recebida",
                        body="Um cliente enviou uma nova reflexão pós-sessão.",
                        data={
                            "type": "new_reflection",
                            "reflection_id": ref.id,
                            "client_id": client_id,
                            "therapist_id": therapist.id,
                        },
                    )
                )

                print(f"✅ [create_reflection] Push enviado com sucesso para reflexão id={ref.id}")

            except Exception as e:
                print(f"❌ [create_reflection] Falha ao enviar push da reflexão {ref.id}: {e}")
        else:
            print(
                f"⚠️ [create_reflection] Nenhum push token ativo encontrado "
                f"para therapist_id={therapist.id}"
            )
    else:
        print(
            f"⚠️ [create_reflection] Push não enviado porque nenhum terapeuta foi encontrado "
            f"para client_id={client_id}"
        )

    print(f"🏁 [create_reflection] Finalizado | reflection_id={ref.id}")
    print("=" * 80 + "\n")

    return ref  # bate com ReflectionOut via from_attributes


def list_my_reflections_with_delete_flag(db: Session, client_id: int):
    print(f"🟡 [list_my_reflections_with_delete_flag] Listando reflexões do client_id={client_id}")

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
                "therapist_id": ref.therapist_id,
                "feeling_after_session": ref.feeling_after_session,
                "what_learned": ref.what_learned,
                "positive_point": ref.positive_point,
                "resistance_or_disagreement": ref.resistance_or_disagreement,
                "created_at": ref.created_at,
                "updated_at": ref.updated_at,
                "can_delete": last_approved_at is None,
            }
        )

    print(
        f"✅ [list_my_reflections_with_delete_flag] Total encontrado para client_id={client_id}: {len(items)}"
    )
    return items


def delete_reflection(db: Session, reflection_id: int, client_id: int):
    print(
        f"🟡 [delete_reflection] Tentando excluir reflection_id={reflection_id} "
        f"do client_id={client_id}"
    )

    ref = (
        db.query(Reflection)
        .filter(Reflection.id == reflection_id, Reflection.client_id == client_id)
        .first()
    )

    if not ref:
        print(
            f"⚠️ [delete_reflection] Reflexão não encontrada | "
            f"reflection_id={reflection_id} client_id={client_id}"
        )
        return False

    approved_exists = (
        db.query(Feedback.id)
        .filter(
            Feedback.reflection_id == reflection_id,
            Feedback.status == "approved",
        )
        .first()
        is not None
    )

    if approved_exists:
        print(
            f"❌ [delete_reflection] Exclusão bloqueada: já existe feedback aprovado "
            f"para reflection_id={reflection_id}"
        )
        raise ValueError("Não é possível excluir: já existe feedback aprovado.")

    db.delete(ref)
    db.commit()

    print(f"✅ [delete_reflection] Reflexão excluída com sucesso | reflection_id={reflection_id}")
    return True


def update_reflection(db: Session, reflection_id: int, client_id: int, data):
    """
    PATCH /reflections/{id}
    - só o dono (client_id) consegue editar
    - bloqueia edição se já existir feedback aprovado
    - updated_at é atualizado pelo onupdate do model
    """
    print(
        f"🟡 [update_reflection] Iniciando atualização | "
        f"reflection_id={reflection_id} client_id={client_id}"
    )
    print(
        f"📦 [update_reflection] Payload recebido: "
        f"feeling_after_session={getattr(data, 'feeling_after_session', None)!r}, "
        f"what_learned={getattr(data, 'what_learned', None)!r}, "
        f"positive_point={getattr(data, 'positive_point', None)!r}, "
        f"resistance_or_disagreement={getattr(data, 'resistance_or_disagreement', None)!r}"
    )

    ref = (
        db.query(Reflection)
        .filter(Reflection.id == reflection_id, Reflection.client_id == client_id)
        .first()
    )

    if not ref:
        print(
            f"⚠️ [update_reflection] Reflexão não encontrada | "
            f"reflection_id={reflection_id} client_id={client_id}"
        )
        return None

    approved_exists = (
        db.query(Feedback.id)
        .filter(
            Feedback.reflection_id == reflection_id,
            Feedback.status == "approved",
        )
        .first()
        is not None
    )

    if approved_exists:
        print(
            f"❌ [update_reflection] Edição bloqueada: já existe feedback aprovado "
            f"para reflection_id={reflection_id}"
        )
        raise ValueError("Não é possível editar: já existe feedback aprovado.")

    ref.feeling_after_session = data.feeling_after_session
    ref.what_learned = data.what_learned
    ref.positive_point = data.positive_point
    ref.resistance_or_disagreement = getattr(data, "resistance_or_disagreement", None)

    if ref.therapist_id is None:
        print(
            f"🔎 [update_reflection] Reflection sem therapist_id. "
            f"Buscando terapeuta para client_id={client_id}"
        )
        therapist = get_therapist_by_client_id(db, client_id)
        if therapist:
            ref.therapist_id = therapist.id
            print(
                f"✅ [update_reflection] therapist_id definido automaticamente: {therapist.id}"
            )
        else:
            print(
                f"⚠️ [update_reflection] Nenhum terapeuta encontrado para client_id={client_id}"
            )

    db.commit()
    db.refresh(ref)

    print(
        f"✅ [update_reflection] Reflexão atualizada com sucesso | "
        f"reflection_id={ref.id} updated_at={ref.updated_at}"
    )

    return ref


# -------------------------
# THERAPIST
# -------------------------
def get_reflection_detail_for_therapist(db: Session, reflection_id: int):
    print(f"🟡 [get_reflection_detail_for_therapist] Buscando detalhes | reflection_id={reflection_id}")

    row = (
        db.query(Reflection, User.name)
        .join(User, User.id == Reflection.client_id)
        .filter(Reflection.id == reflection_id)
        .first()
    )

    if not row:
        print(
            f"⚠️ [get_reflection_detail_for_therapist] Reflexão não encontrada | "
            f"reflection_id={reflection_id}"
        )
        return None

    ref, client_name = row

    print(
        f"✅ [get_reflection_detail_for_therapist] Detalhe encontrado | "
        f"reflection_id={ref.id} client_name={client_name}"
    )

    return {
        "id": ref.id,
        "client_id": ref.client_id,
        "therapist_id": ref.therapist_id,
        "client_name": client_name,
        "feeling_after_session": ref.feeling_after_session,
        "what_learned": ref.what_learned,
        "positive_point": ref.positive_point,
        "resistance_or_disagreement": ref.resistance_or_disagreement,
        "created_at": ref.created_at,
        "updated_at": ref.updated_at,
    }


def list_pending_reflections(db: Session):
    """
    Pendentes = reflection sem feedback aprovado.
    Evita duplicar quando existe mais de um feedback por reflection,
    pegando apenas o último feedback (por created_at).
    """
    print("🟡 [list_pending_reflections] Listando reflexões pendentes")

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
                "therapist_id": ref.therapist_id,
                "client_name": client_name,
                "feeling_after_session": ref.feeling_after_session,
                "created_at": ref.created_at,
            }
        )

    print(f"✅ [list_pending_reflections] Total pendentes: {len(items)}")
    return items