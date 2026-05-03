from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user

from app.modules.invitations.schemas import (
    InviteCreate,
    InviteResponse,
    InviteValidateResponse,
    SignupFromInvite,
)

from app.modules.invitations.service import (
    create_invitation,
    validate_invitation,
    signup_from_invitation,
)

from app.modules.users.schemas import UserOut
from app.modules.users.service import serialize_user
from app.core.email import send_email

router = APIRouter(prefix="/invitations", tags=["Invitations"])


def require_therapist(user=Depends(get_current_user)):
    if getattr(user, "role", None) != "therapist":
        raise HTTPException(status_code=403, detail="Forbidden")
    return user


@router.post("", response_model=InviteResponse)
def create_invitation_route(
    payload: InviteCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_therapist),
):
    inv, token = create_invitation(
        db,
        therapist_id=current_user.id,
        email=payload.email,
    )

    send_email(
        to=inv.email,
        subject="Convite para o EloMind",
        body=f"Seu código de convite é: {token}",
    )

    return {"ok": True, "email": inv.email}


@router.get("/validate", response_model=InviteValidateResponse)
def validate_invitation_route(token: str, db: Session = Depends(get_db)):
    inv = validate_invitation(db, token=token)
    if not inv:
        return {"valid": False, "email": None}
    return {"valid": True, "email": inv.email}


@router.post("/signup", response_model=UserOut)
def signup_from_invitation_route(
    payload: SignupFromInvite,
    db: Session = Depends(get_db),
):
    user = signup_from_invitation(
        db,
        token=payload.token,
        name=payload.name,
        password=payload.password,
    )

    if not user:
        raise HTTPException(400, "Invalid or expired invite")

    return serialize_user(user)
