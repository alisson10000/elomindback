from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.modules.audit.service import get_client_ip, get_user_agent
from app.modules.feedback.schemas import (
    FeedbackApproveIn,
    FeedbackOut,
    FeedbackRejectIn,
)
from app.modules.feedback.service import (
    approve,
    generate_for_reflection,
    get_by_reflection_for_client,
    get_by_reflection_for_therapist,
    list_by_client_for_therapist,
    list_pending,
    reject,
)

router = APIRouter(tags=["Feedback"])


def require_role(role: str):
    def _dep(user=Depends(get_current_user)):
        if getattr(user, "role", None) != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )
        return user

    return _dep


@router.post("/generate/{reflection_id}", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
def generate(
    reflection_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("therapist")),
):
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
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_role("therapist")),
):
    return approve(
        db,
        feedback_id=feedback_id,
        therapist_id=user.id,
        update_data=payload,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )


@router.patch("/{feedback_id}/reject", response_model=FeedbackOut)
def reject_route(
    feedback_id: int,
    payload: FeedbackRejectIn,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_role("therapist")),
):
    return reject(
        db,
        feedback_id=feedback_id,
        therapist_id=user.id,
        notes=payload.therapist_notes,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )


@router.get("/therapist/by-reflection/{reflection_id}", response_model=FeedbackOut)
def therapist_by_reflection(
    reflection_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("therapist")),
):
    return get_by_reflection_for_therapist(
        db,
        reflection_id=reflection_id,
    )


@router.get("/by-client/{client_id}", response_model=list[FeedbackOut])
def by_client(
    client_id: int,
    status: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_role("therapist")),
):
    statuses = None
    if status:
        statuses = [s.strip() for s in status.split(",") if s and s.strip()]

    return list_by_client_for_therapist(
        db,
        client_id=client_id,
        statuses=statuses,
    )


@router.get("/by-reflection/{reflection_id}", response_model=FeedbackOut)
def client_by_reflection(
    reflection_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("client")),
):
    return get_by_reflection_for_client(
        db,
        reflection_id=reflection_id,
        client_id=user.id,
    )
