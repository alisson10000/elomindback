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
)

router = APIRouter()


def _ensure_role(user, role: str):
    if getattr(user, "role", None) != role:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/generate/{reflection_id}", response_model=FeedbackOut)
def generate(reflection_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # MVP: apenas terapeuta gera (ou você pode deixar interno depois)
    _ensure_role(user, "therapist")
    return generate_for_reflection(db, reflection_id=reflection_id)


@router.get("/pending", response_model=list[FeedbackOut])
def pending(db: Session = Depends(get_db), user=Depends(get_current_user)):
    _ensure_role(user, "therapist")
    return list_pending(db)


@router.patch("/{feedback_id}/approve", response_model=FeedbackOut)
def approve_route(
    feedback_id: int,
    payload: FeedbackApproveIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ensure_role(user, "therapist")
    return approve(db, feedback_id=feedback_id, therapist_id=user.id, update_data=payload)


@router.patch("/{feedback_id}/reject", response_model=FeedbackOut)
def reject_route(
    feedback_id: int,
    payload: FeedbackRejectIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _ensure_role(user, "therapist")
    return reject(db, feedback_id=feedback_id, therapist_id=user.id, notes=payload.therapist_notes)


@router.get("/by-reflection/{reflection_id}", response_model=FeedbackOut)
def by_reflection(reflection_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    # cliente só vê se approved e se a reflexão é dele
    _ensure_role(user, "client")
    return get_by_reflection_for_client(db, reflection_id=reflection_id, client_id=user.id)
