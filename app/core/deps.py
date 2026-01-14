from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import decode_token
from app.modules.users.service import get_user_by_email

bearer = HTTPBearer()

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
):
    token = creds.credentials
    try:
        payload = decode_token(token)
        email = payload.get("sub")
        if not email:
            raise ValueError("Missing sub")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = get_user_by_email(db, email=email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
