from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user

from app.modules.dreams.schemas import (
    DreamCreate,
    DreamClientSavedOut,
    DreamOut,
    DreamTherapistUpdate,
)
from app.modules.dreams.service import (
    create_dream,
    list_dreams_by_client,
    update_dream_as_therapist,
)

router = APIRouter(tags=["Dreams"])


def require_client(user=Depends(get_current_user)):
    if getattr(user, "role", None) != "client":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return user


def require_therapist(user=Depends(get_current_user)):
    if getattr(user, "role", None) != "therapist":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return user


# -------------------------
# CLIENT
# -------------------------
@router.post("", response_model=DreamClientSavedOut)
def create_dream_client(
    payload: DreamCreate,
    db: Session = Depends(get_db),
    user=Depends(require_client),
):
    """
    Cliente cria sonho.
    Regra: cliente não poderá visualizar depois (não existe GET).
    Retorno mínimo: id e created_at.
    """
    d = create_dream(db, client_id=user.id, description=payload.description)
    return d


# -------------------------
# THERAPIST
# -------------------------
@router.get("/{client_id}", response_model=list[DreamOut])
def list_dreams_for_client(
    client_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_therapist),
):
    return list_dreams_by_client(db, therapist_id=user.id, client_id=client_id)


@router.patch("/{dream_id}", response_model=DreamOut)
def update_dream(
    dream_id: int,
    payload: DreamTherapistUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_therapist),
):
    return update_dream_as_therapist(
        db,
        therapist_id=user.id,
        dream_id=dream_id,
        update_data=payload,
    )
