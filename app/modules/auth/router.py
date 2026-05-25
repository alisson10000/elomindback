from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.core.security import decode_token
from app.core.rate_limit import LOGIN_RATE_LIMIT, SIGNUP_RATE_LIMIT, limiter
from app.modules.audit.service import get_client_ip, get_user_agent, log_action
from app.modules.auth.jwt_service import exp_to_datetime_utc, jti_prefix, revoke_token
from app.modules.auth.schemas import SignupIn, LoginIn, TokenOut, MeOut
from app.modules.auth.service import signup, login
from app.modules.users.service import serialize_user

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)


@router.post("/signup", response_model=TokenOut)
@limiter.limit(SIGNUP_RATE_LIMIT)
def signup_route(
    request: Request,
    response: Response,
    payload: SignupIn,
    db: Session = Depends(get_db),
):
    token = signup(
        db,
        email=payload.email,
        name=payload.name,
        role=payload.role,
        password=payload.password,
    )
    return {"access_token": token}


@router.post("/login", response_model=TokenOut)
@limiter.limit(LOGIN_RATE_LIMIT)
def login_route(
    payload: LoginIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    token = login(
        db,
        email=payload.email,
        password=payload.password,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return {"access_token": token}


@router.post("/logout")
def logout_route(
    request: Request,
    db: Session = Depends(get_db),
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    user=Depends(get_current_user),
):
    token = creds.credentials if creds else None
    token_jti = None
    expires_at = None

    if token:
        try:
            payload = decode_token(token)
            token_jti = payload.get("jti")
            expires_at = exp_to_datetime_utc(payload.get("exp"))
            if expires_at is not None:
                expires_at = expires_at.replace(tzinfo=None)
        except Exception:
            token_jti = None
            expires_at = None

    if token_jti:
        created = revoke_token(
            db,
            token_jti=str(token_jti),
            user_id=getattr(user, "id", None),
            expires_at=expires_at,
        )
        log_action(
            db,
            user_id=user.id,
            action="TOKEN_REVOKED",
            resource_type="auth",
            resource_id=user.id,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            details={
                "jti_prefix": jti_prefix(str(token_jti)),
                "created": created,
            },
        )
    else:
        # TODO(security): quando todos os clientes estiverem emitindo `jti`, logout deve sempre revogar.
        pass

    log_action(
        db,
        user_id=user.id,
        action="LOGOUT",
        resource_type="auth",
        resource_id=user.id,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        details={"role": getattr(user, "role", None)},
    )
    return {"ok": True}


@router.get("/me", response_model=MeOut)
def me_route(user=Depends(get_current_user)):
    return serialize_user(user)
