from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.modules.audit.service import log_action
from app.modules.auth.jwt_service import is_token_revoked, jti_prefix
from app.modules.users.service import get_user_by_email, get_user_by_id

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
):
    if not creds or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token",
        )

    token = creds.credentials

    try:
        payload = decode_token(token)
        subject = payload.get("sub")
        if not subject:
            raise ValueError("Missing sub")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    token_jti = payload.get("jti")
    if token_jti:
        if is_token_revoked(db, str(token_jti)):
            # Segurança: nunca logar JWT completo nem payload completo.
            log_action(
                db,
                action="TOKEN_REJECTED_REVOKED",
                resource_type="auth",
                details={"jti_prefix": jti_prefix(str(token_jti))},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
            )
    else:
        # TODO(security): remover compatibilidade com tokens sem `jti` após migração dos clientes.
        pass

    user = None
    if str(subject).isdigit():
        user = get_user_by_id(db, user_id=int(subject))
    else:
        user = get_user_by_email(db, email=str(subject))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not getattr(user, "is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User inactive",
        )

    return user
