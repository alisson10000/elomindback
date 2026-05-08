from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.email import send_email
from app.core.rate_limit import INVITATION_CREATE_RATE_LIMIT, INVITATION_SIGNUP_RATE_LIMIT, limiter
from app.db.session import get_db
from app.modules.audit.service import get_client_ip, get_user_agent
from app.modules.invitations.schemas import (
    InviteCreate,
    InviteResponse,
    InviteValidateResponse,
    SignupFromInvite,
)
from app.modules.invitations.service import (
    create_invitation,
    signup_from_invitation,
    validate_invitation,
)
from app.modules.users.schemas import UserOut
from app.modules.users.service import serialize_user

router = APIRouter(prefix="/invitations", tags=["Invitations"])


def require_therapist(user=Depends(get_current_user)):
    if getattr(user, "role", None) != "therapist":
        raise HTTPException(status_code=403, detail="Forbidden")
    return user


@router.post("", response_model=InviteResponse)
@limiter.limit(INVITATION_CREATE_RATE_LIMIT)
def create_invitation_route(
    payload: InviteCreate,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user=Depends(require_therapist),
):
    inv, token = create_invitation(
        db,
        therapist_id=current_user.id,
        email=payload.email,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    send_email(
        to=inv.email,
        subject="Convite para o EloMind",
        body=f"Seu cÃ³digo de convite Ã©: {token}",
    )

    return {"ok": True, "email": inv.email}


@router.get("/validate", response_model=InviteValidateResponse)
def validate_invitation_route(token: str, db: Session = Depends(get_db)):
    inv = validate_invitation(db, token=token)
    if not inv:
        return {"valid": False, "email": None}
    return {"valid": True, "email": inv.email}


@router.post("/signup", response_model=UserOut)
@limiter.limit(INVITATION_SIGNUP_RATE_LIMIT)
def signup_from_invitation_route(
    payload: SignupFromInvite,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    user = signup_from_invitation(
        db,
        token=payload.token,
        name=payload.name,
        password=payload.password,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    if not user:
        raise HTTPException(400, "Invalid or expired invite")

    return serialize_user(user)
