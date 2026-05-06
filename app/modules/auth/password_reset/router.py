from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.audit.service import get_client_ip, get_user_agent, log_action

from app.modules.auth.password_reset.schemas import (
    ForgotPasswordIn,
    ForgotPasswordOut,
    ResetPasswordIn,
    ResetPasswordOut,
)
from app.modules.auth.password_reset.service import (
    create_password_reset,
    reset_password_with_token,
)

try:
    from app.core.email import send_email  # type: ignore
except Exception:
    def send_email(*args, **kwargs):
        print("\n[DEV EMAIL] =====")
        print("ARGS:", args)
        print("KWARGS:", kwargs)
        print("===== [DEV EMAIL]\n")


router = APIRouter(tags=["Auth"])


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordOut,
    status_code=status.HTTP_200_OK,
)
def forgot_password(payload: ForgotPasswordIn, request: Request, db: Session = Depends(get_db)):
    """
    Sempre retorna ok=True para evitar enumeraÃ§Ã£o de emails.
    Se o email existir, cria token e envia o token/cÃ³digo por email.
    """
    result = create_password_reset(db, email=payload.email)
    user = None

    if result:
        token_plain, user = result

        subject = "EloMind - RedefiniÃ§Ã£o de senha"
        body = (
            "VocÃª solicitou redefiniÃ§Ã£o de senha.\n\n"
            "Use o cÃ³digo/token abaixo no aplicativo para criar uma nova senha:\n\n"
            f"{token_plain}\n\n"
            "Se vocÃª nÃ£o solicitou, ignore esta mensagem."
        )

        send_email(user.email, subject, body)

    log_action(
        db,
        user_id=getattr(user, "id", None),
        action="PASSWORD_RESET_REQUEST",
        resource_type="auth",
        resource_id=getattr(user, "id", None),
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        details={"email": payload.email, "user_exists": bool(result)},
    )

    return {"ok": True}


@router.post(
    "/reset-password",
    response_model=ResetPasswordOut,
    status_code=status.HTTP_200_OK,
)
def reset_password(payload: ResetPasswordIn, request: Request, db: Session = Depends(get_db)):
    """
    Recebe email + token + nova senha e efetiva a troca.
    """
    try:
        reset_password_with_token(
            db,
            email=payload.email,
            token=payload.token,
            new_password=payload.password,
        )
        log_action(
            db,
            action="PASSWORD_RESET_SUCCESS",
            resource_type="auth",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            details={"email": payload.email},
        )
        return {"ok": True}

    except ValueError as e:
        msg = str(e).lower()

        if "expired" in msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token expired",
            )
        if "used" in msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token already used",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token",
        )
