from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user

from app.modules.push_tokens.schemas import (
    PushTokenCreate,
    PushTokenOut,
    PushTokenDeactivate,
)
from app.modules.push_tokens.service import (
    save_push_token,
    list_user_push_tokens,
    deactivate_push_token,
)

router = APIRouter(tags=["Push Tokens"])


@router.post("/", response_model=PushTokenOut, status_code=status.HTTP_201_CREATED)
def register_push_token(
    payload: PushTokenCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    token = save_push_token(
        db=db,
        user_id=user.id,
        token=payload.expo_push_token,
        platform=payload.platform,
    )
    return token


@router.get("/me", response_model=list[PushTokenOut])
def my_push_tokens(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return list_user_push_tokens(db=db, user_id=user.id)


@router.post("/deactivate")
def deactivate_my_push_token(
    payload: PushTokenDeactivate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    ok = deactivate_push_token(
        db=db,
        user_id=user.id,
        token=payload.expo_push_token,
    )

    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Push token not found",
        )

    return {"message": "Push token desativado com sucesso"}