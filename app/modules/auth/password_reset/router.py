from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db

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

# Se existir helper real, usa. Se não existir, cai no print sem quebrar.
try:
    from app.core.email import send_email  # type: ignore
except Exception:
    def send_email(*args, **kwargs):
        print("\n📩 [DEV EMAIL] =====")
        print("ARGS:", args)
        print("KWARGS:", kwargs)
        print("===== [DEV EMAIL] 📩\n")


# ✅ SEM prefix aqui, porque o main.py já tem prefix no include_router
router = APIRouter(tags=["Auth"])


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordOut,
    status_code=status.HTTP_200_OK,
)
def forgot_password(payload: ForgotPasswordIn, db: Session = Depends(get_db)):
    """
    Sempre retorna ok=True para evitar enumeração de emails.
    Se o email existir, cria token e envia o token/código por email.
    """
    result = create_password_reset(db, email=payload.email)

    if result:
        token_plain, user = result

        subject = "EloMind - Redefinição de senha"
        body = (
            "Você solicitou redefinição de senha.\n\n"
            "Use o código/token abaixo no aplicativo para criar uma nova senha:\n\n"
            f"{token_plain}\n\n"
            "Se você não solicitou, ignore esta mensagem."
        )

        # chamada posicional pra não depender da assinatura do helper
        send_email(user.email, subject, body)

    return {"ok": True}


@router.post(
    "/reset-password",
    response_model=ResetPasswordOut,
    status_code=status.HTTP_200_OK,
)
def reset_password(payload: ResetPasswordIn, db: Session = Depends(get_db)):
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

        # Mantém resposta genérica (segurança)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token",
        )
