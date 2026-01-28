from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.modules.reflections.schemas import (
    ReflectionCreate,
    ReflectionOut,
    ReflectionOutWithFlags,
    ReflectionPendingOut,
    ReflectionDetailOut,
)
from app.modules.reflections.service import (
    create_reflection,
    delete_reflection,
    list_my_reflections_with_delete_flag,
    list_pending_reflections,
    get_reflection_detail_for_therapist,
)

router = APIRouter(tags=["Reflections"])


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
@router.post("/", response_model=ReflectionOut)
def create(
    payload: ReflectionCreate,
    db: Session = Depends(get_db),
    user=Depends(require_client),
):
    return create_reflection(db, client_id=user.id, data=payload)


@router.get("/me", response_model=list[ReflectionOutWithFlags])
def my_history(
    db: Session = Depends(get_db),
    user=Depends(require_client),
):
    return list_my_reflections_with_delete_flag(db, client_id=user.id)


@router.delete("/{reflection_id}")
def delete_route(
    reflection_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_client),
):
    try:
        ok = delete_reflection(db, reflection_id=reflection_id, client_id=user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not ok:
        raise HTTPException(status_code=404, detail="Reflection not found")

    return {"message": "Reflection deleted successfully"}


# -------------------------
# THERAPIST
# -------------------------
@router.get("/pending", response_model=list[ReflectionPendingOut])
def pending_route(
    db: Session = Depends(get_db),
    _: object = Depends(require_therapist),
):
    return list_pending_reflections(db)


@router.get("/{reflection_id}", response_model=ReflectionDetailOut)
def detail_route(
    reflection_id: int,
    db: Session = Depends(get_db),
    _: object = Depends(require_therapist),
):
    data = get_reflection_detail_for_therapist(db, reflection_id)
    if not data:
        raise HTTPException(status_code=404, detail="Reflection not found")
    return data
