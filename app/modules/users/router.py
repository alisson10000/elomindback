from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.modules.users.schemas import UserOut, UserStatusUpdate
from app.modules.users.service import get_user_by_id, list_clients, set_user_active

router = APIRouter(prefix="/users", tags=["Users"])


def require_therapist(user=Depends(get_current_user)):
    if getattr(user, "role", None) != "therapist":
        raise HTTPException(status_code=403, detail="Forbidden")
    return user


@router.get("/clients", response_model=list[UserOut])
def list_clients_route(
    db: Session = Depends(get_db),
    _: object = Depends(require_therapist),
):
    return list_clients(db)


@router.patch("/{user_id}/status", response_model=UserOut)
def update_user_status_route(
    user_id: int,
    payload: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_therapist),
):
    target = get_user_by_id(db, user_id=user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot change your own status")

    if target.role != "client":
        raise HTTPException(status_code=400, detail="Only clients can be activated/deactivated")

    return set_user_active(db, user=target, is_active=payload.is_active)
