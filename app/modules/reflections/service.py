from __future__ import annotations

import asyncio

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_text, encrypt_text
from app.modules.feedback.model import Feedback
from app.modules.push_tokens.service import get_user_push_tokens, send_expo_push
from app.modules.reflections.model import Reflection
from app.modules.therapist_clients.model import TherapistClient
from app.modules.users.model import User
from app.modules.users.service import serialize_user


def get_therapist_by_client_id(db: Session, client_id: int):
    print(f"DEBUG [get_therapist_by_client_id] client_id={client_id}")

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
        print(f"INFO [get_therapist_by_client_id] therapist_id={therapist.id}")
    else:
        print(f"WARN [get_therapist_by_client_id] therapist not found for client_id={client_id}")

    return therapist


def _serialize_reflection(ref: Reflection) -> dict:
    return {
        "id": ref.id,
        "client_id": ref.client_id,
        "therapist_id": ref.therapist_id,
        "feeling_after_session": decrypt_text(ref.feeling_after_session),
        "what_learned": decrypt_text(ref.what_learned),
        "positive_point": decrypt_text(ref.positive_point),
        "resistance_or_disagreement": decrypt_text(ref.resistance_or_disagreement),
        "created_at": ref.created_at,
        "updated_at": ref.updated_at,
    }


def create_reflection(db: Session, client_id: int, data):
    print("\n" + "=" * 80)
    print(f"DEBUG [create_reflection] start client_id={client_id}")
    print(
        "DEBUG [create_reflection] payload received for encrypted reflection fields"
    )

    therapist = get_therapist_by_client_id(db, client_id)

    ref = Reflection(
        client_id=client_id,
        therapist_id=therapist.id if therapist else None,
        feeling_after_session=encrypt_text(data.feeling_after_session),
        what_learned=encrypt_text(data.what_learned),
        positive_point=encrypt_text(data.positive_point),
        resistance_or_disagreement=encrypt_text(getattr(data, "resistance_or_disagreement", None)),
    )

    print(
        f"DEBUG [create_reflection] prepared reflection client_id={ref.client_id} "
        f"therapist_id={ref.therapist_id}"
    )

    db.add(ref)
    print("DEBUG [create_reflection] saving reflection")
    db.commit()
    db.refresh(ref)

    print(
        f"INFO [create_reflection] created reflection_id={ref.id} "
        f"therapist_id={ref.therapist_id}"
    )

    if therapist:
        print(f"DEBUG [create_reflection] loading push tokens therapist_id={therapist.id}")

        tokens = get_user_push_tokens(db, therapist.id)
        print(
            f"DEBUG [create_reflection] push tokens loaded therapist_id={therapist.id} "
            f"count={len(tokens) if tokens else 0}"
        )

        if tokens:
            try:
                asyncio.run(
                    send_expo_push(
                        db=db,
                        push_tokens=tokens,
                        title="Nova reflexÃ£o recebida",
                        body="Um cliente enviou uma nova reflexÃ£o pÃ³s-sessÃ£o.",
                        data={
                            "type": "new_reflection",
                            "reflection_id": ref.id,
                            "client_id": client_id,
                            "therapist_id": therapist.id,
                        },
                    )
                )

                print(f"INFO [create_reflection] push sent reflection_id={ref.id}")

            except Exception as exc:
                print(f"ERROR [create_reflection] push failed reflection_id={ref.id}: {exc}")
        else:
            print(f"WARN [create_reflection] no active push tokens therapist_id={therapist.id}")
    else:
        print(f"WARN [create_reflection] therapist not found for client_id={client_id}")

    print(f"INFO [create_reflection] finished reflection_id={ref.id}")
    print("=" * 80 + "\n")

    return _serialize_reflection(ref)


def list_my_reflections_with_delete_flag(db: Session, client_id: int):
    print(f"DEBUG [list_my_reflections_with_delete_flag] client_id={client_id}")

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
                "feeling_after_session": decrypt_text(ref.feeling_after_session),
                "what_learned": decrypt_text(ref.what_learned),
                "positive_point": decrypt_text(ref.positive_point),
                "resistance_or_disagreement": decrypt_text(ref.resistance_or_disagreement),
                "created_at": ref.created_at,
                "updated_at": ref.updated_at,
                "can_delete": last_approved_at is None,
            }
        )

    print(f"INFO [list_my_reflections_with_delete_flag] count={len(items)} client_id={client_id}")
    return items


def delete_reflection(db: Session, reflection_id: int, client_id: int):
    print(f"DEBUG [delete_reflection] reflection_id={reflection_id} client_id={client_id}")

    ref = (
        db.query(Reflection)
        .filter(Reflection.id == reflection_id, Reflection.client_id == client_id)
        .first()
    )

    if not ref:
        print(f"WARN [delete_reflection] reflection not found reflection_id={reflection_id}")
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
        print(f"ERROR [delete_reflection] approved feedback exists reflection_id={reflection_id}")
        raise ValueError("NÃ£o Ã© possÃ­vel excluir: jÃ¡ existe feedback aprovado.")

    db.delete(ref)
    db.commit()

    print(f"INFO [delete_reflection] deleted reflection_id={reflection_id}")
    return True


def update_reflection(db: Session, reflection_id: int, client_id: int, data):
    print(f"DEBUG [update_reflection] reflection_id={reflection_id} client_id={client_id}")
    print("DEBUG [update_reflection] payload received for encrypted reflection fields")

    ref = (
        db.query(Reflection)
        .filter(Reflection.id == reflection_id, Reflection.client_id == client_id)
        .first()
    )

    if not ref:
        print(f"WARN [update_reflection] reflection not found reflection_id={reflection_id}")
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
        print(f"ERROR [update_reflection] approved feedback exists reflection_id={reflection_id}")
        raise ValueError("NÃ£o Ã© possÃ­vel editar: jÃ¡ existe feedback aprovado.")

    ref.feeling_after_session = encrypt_text(data.feeling_after_session)
    ref.what_learned = encrypt_text(data.what_learned)
    ref.positive_point = encrypt_text(data.positive_point)
    ref.resistance_or_disagreement = encrypt_text(getattr(data, "resistance_or_disagreement", None))

    if ref.therapist_id is None:
        therapist = get_therapist_by_client_id(db, client_id)
        if therapist:
            ref.therapist_id = therapist.id
            print(f"INFO [update_reflection] therapist linked therapist_id={therapist.id}")
        else:
            print(f"WARN [update_reflection] therapist not found for client_id={client_id}")

    db.commit()
    db.refresh(ref)

    print(f"INFO [update_reflection] updated reflection_id={ref.id}")
    return _serialize_reflection(ref)


def get_reflection_detail_for_therapist(db: Session, reflection_id: int):
    print(f"DEBUG [get_reflection_detail_for_therapist] reflection_id={reflection_id}")

    row = (
        db.query(Reflection, User)
        .join(User, User.id == Reflection.client_id)
        .filter(Reflection.id == reflection_id)
        .first()
    )

    if not row:
        print(f"WARN [get_reflection_detail_for_therapist] reflection not found reflection_id={reflection_id}")
        return None

    ref, client = row
    client_name = serialize_user(client)["name"]

    print(f"INFO [get_reflection_detail_for_therapist] found reflection_id={ref.id}")

    return {
        "id": ref.id,
        "client_id": ref.client_id,
        "therapist_id": ref.therapist_id,
        "client_name": client_name,
        "feeling_after_session": decrypt_text(ref.feeling_after_session),
        "what_learned": decrypt_text(ref.what_learned),
        "positive_point": decrypt_text(ref.positive_point),
        "resistance_or_disagreement": decrypt_text(ref.resistance_or_disagreement),
        "created_at": ref.created_at,
        "updated_at": ref.updated_at,
    }


def list_pending_reflections(db: Session):
    print("DEBUG [list_pending_reflections] listing pending reflections")

    last_fb_sq = (
        db.query(
            Feedback.reflection_id.label("rid"),
            func.max(Feedback.created_at).label("last_created_at"),
        )
        .group_by(Feedback.reflection_id)
        .subquery()
    )

    q = (
        db.query(Reflection, User, Feedback.status)
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
    for ref, client, fb_status in q.all():
        client_name = serialize_user(client)["name"]
        items.append(
            {
                "id": ref.id,
                "client_id": ref.client_id,
                "therapist_id": ref.therapist_id,
                "client_name": client_name,
                "feeling_after_session": decrypt_text(ref.feeling_after_session),
                "created_at": ref.created_at,
            }
        )

    print(f"INFO [list_pending_reflections] total={len(items)}")
    return items
