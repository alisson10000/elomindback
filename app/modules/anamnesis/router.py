from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user

from app.modules.anamnesis.schemas import AnamnesisCreate, AnamnesisUpdate, AnamnesisOut
from app.modules.anamnesis.service import get_anamnesis_by_client, create_anamnesis, update_anamnesis

router = APIRouter( tags=["Anamnesis"])


def require_therapist(user=Depends(get_current_user)):
    if getattr(user, "role", None) != "therapist":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return user


@router.post("/{client_id}", response_model=AnamnesisOut)
def create_route(
    client_id: int,
    payload: AnamnesisCreate,
    db: Session = Depends(get_db),
    user=Depends(require_therapist),
):
    try:
        return create_anamnesis(db, therapist_id=user.id, client_id=client_id, summary=payload.summary)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Client not linked to therapist")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{client_id}", response_model=AnamnesisOut)
def get_route(
    client_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_therapist),
):
    try:
        row = get_anamnesis_by_client(db, therapist_id=user.id, client_id=client_id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Client not linked to therapist")

    if not row:
        raise HTTPException(status_code=404, detail="Anamnese not found")
    return row


@router.patch("/{client_id}", response_model=AnamnesisOut)
def patch_route(
    client_id: int,
    payload: AnamnesisUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_therapist),
):
    try:
        row = update_anamnesis(db, therapist_id=user.id, client_id=client_id, summary=payload.summary)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Client not linked to therapist")

    if not row:
        raise HTTPException(status_code=404, detail="Anamnese not found")
    return row
