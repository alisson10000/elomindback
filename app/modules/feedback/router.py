from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.modules.feedback.schemas import FeedbackOut, FeedbackApproveIn, FeedbackRejectIn
from app.modules.feedback.service import (
    generate_for_reflection,
    list_pending,
    approve,
    reject,
    get_by_reflection_for_client,
    get_by_reflection_for_therapist,  # ✅ novo
)

router = APIRouter()


def require_role(role: str):
    def _dep(user=Depends(get_current_user)):
        if getattr(user, "role", None) != role:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user
    return _dep


@router.post("/generate/{reflection_id}", response_model=FeedbackOut)
def generate(
    reflection_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("therapist")),
):
    # MVP: apenas terapeuta gera
    return generate_for_reflection(db, reflection_id=reflection_id)


@router.get("/pending", response_model=list[FeedbackOut])
def pending(
    db: Session = Depends(get_db),
    user=Depends(require_role("therapist")),
):
    return list_pending(db)


@router.patch("/{feedback_id}/approve", response_model=FeedbackOut)
def approve_route(
    feedback_id: int,
    payload: FeedbackApproveIn,
    db: Session = Depends(get_db),
    user=Depends(require_role("therapist")),
):
    return approve(db, feedback_id=feedback_id, therapist_id=user.id, update_data=payload)


@router.patch("/{feedback_id}/reject", response_model=FeedbackOut)
def reject_route(
    feedback_id: int,
    payload: FeedbackRejectIn,
    db: Session = Depends(get_db),
    user=Depends(require_role("therapist")),
):
    return reject(db, feedback_id=feedback_id, therapist_id=user.id, notes=payload.therapist_notes)


# ✅ Novo: terapeuta buscar feedback por reflexão (qualquer status)
@router.get("/therapist/by-reflection/{reflection_id}", response_model=FeedbackOut)
def therapist_by_reflection(
    reflection_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("therapist")),
):
    return get_by_reflection_for_therapist(db, reflection_id=reflection_id)


# Mantém: client-only (só approved e só se a reflexão é dele)
@router.get("/by-reflection/{reflection_id}", response_model=FeedbackOut)
def client_by_reflection(
    reflection_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("client")),
):
    return get_by_reflection_for_client(db, reflection_id=reflection_id, client_id=user.id)
