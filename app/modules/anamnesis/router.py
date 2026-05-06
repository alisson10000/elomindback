from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.modules.anamnesis.schemas import AnamnesisCreate, AnamnesisOut, AnamnesisUpdate
from app.modules.anamnesis.service import create_anamnesis, get_anamnesis_by_client, update_anamnesis
from app.modules.audit.service import get_client_ip, get_user_agent

router = APIRouter(tags=["Anamnesis"])


def require_therapist(user=Depends(get_current_user)):
    if getattr(user, "role", None) != "therapist":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return user


@router.post("/{client_id}", response_model=AnamnesisOut)
def create_route(
    client_id: int,
    payload: AnamnesisCreate,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_therapist),
):
    try:
        return create_anamnesis(
            db,
            therapist_id=user.id,
            client_id=client_id,
            summary=payload.summary,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Client not linked to therapist")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{client_id}", response_model=AnamnesisOut)
def get_route(
    client_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_therapist),
):
    try:
        row = get_anamnesis_by_client(
            db,
            therapist_id=user.id,
            client_id=client_id,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Client not linked to therapist")

    if not row:
        raise HTTPException(status_code=404, detail="Anamnese not found")
    return row


@router.patch("/{client_id}", response_model=AnamnesisOut)
def patch_route(
    client_id: int,
    payload: AnamnesisUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_therapist),
):
    try:
        row = update_anamnesis(
            db,
            therapist_id=user.id,
            client_id=client_id,
            summary=payload.summary,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Client not linked to therapist")

    if not row:
        raise HTTPException(status_code=404, detail="Anamnese not found")
    return row
