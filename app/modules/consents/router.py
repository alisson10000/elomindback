from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user

from app.modules.consents.schemas import ConsentMeOut, ConsentAcceptIn, ConsentOut
from app.modules.consents.service import get_consent_by_client_id, accept_consent

router = APIRouter(prefix="/consents", tags=["Consents"])


@router.get("/me", response_model=ConsentMeOut)
def get_my_consent(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if getattr(current_user, "role", None) != "client":
        raise HTTPException(status_code=403, detail="Only clients")

    consent = get_consent_by_client_id(db, current_user.id)
    if not consent:
        return {"accepted": False, "accepted_at": None}

    return {"accepted": True, "accepted_at": consent.accepted_at}


@router.post("", response_model=ConsentOut)
def accept_my_consent(
    payload: ConsentAcceptIn,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if getattr(current_user, "role", None) != "client":
        raise HTTPException(status_code=403, detail="Only clients")

    if payload.accepted is not True:
        raise HTTPException(status_code=400, detail="Consent must be accepted")

    consent = accept_consent(db, client_id=current_user.id)
    return consent
