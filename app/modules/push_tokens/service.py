from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.modules.push_tokens.model import UserPushToken


EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def save_push_token(
    db: Session,
    user_id: int,
    token: str,
    platform: str | None = None,
):
    """
    Salva ou atualiza um token push.
    - se o token já existir, reativa e vincula ao user atual
    - se não existir, cria
    """
    existing = (
        db.query(UserPushToken)
        .filter(UserPushToken.expo_push_token == token)
        .first()
    )

    if existing:
        existing.user_id = user_id
        existing.platform = platform
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        return existing

    new_token = UserPushToken(
        user_id=user_id,
        expo_push_token=token,
        platform=platform,
        is_active=True,
    )
    db.add(new_token)
    db.commit()
    db.refresh(new_token)
    return new_token


def get_user_push_tokens(db: Session, user_id: int) -> list[str]:
    """
    Retorna apenas os tokens ativos do usuário.
    """
    rows = (
        db.query(UserPushToken.expo_push_token)
        .filter(
            UserPushToken.user_id == user_id,
            UserPushToken.is_active.is_(True),
        )
        .all()
    )
    return [row[0] for row in rows]


def list_user_push_tokens(db: Session, user_id: int):
    """
    Lista os registros completos de tokens do usuário.
    """
    return (
        db.query(UserPushToken)
        .filter(UserPushToken.user_id == user_id)
        .order_by(UserPushToken.created_at.desc())
        .all()
    )


def deactivate_push_token(db: Session, user_id: int, token: str) -> bool:
    """
    Desativa um token específico do usuário.
    """
    row = (
        db.query(UserPushToken)
        .filter(
            UserPushToken.user_id == user_id,
            UserPushToken.expo_push_token == token,
        )
        .first()
    )

    if not row:
        return False

    row.is_active = False
    db.commit()
    db.refresh(row)
    return True


def deactivate_invalid_tokens(db: Session, tokens: list[str]) -> None:
    """
    Desativa tokens inválidos retornados pelo Expo.
    """
    if not tokens:
        return

    (
        db.query(UserPushToken)
        .filter(UserPushToken.expo_push_token.in_(tokens))
        .update({"is_active": False}, synchronize_session=False)
    )
    db.commit()


def _extract_invalid_tokens_from_expo_response(
    push_tokens: list[str],
    expo_response_data: list[dict[str, Any]],
) -> list[str]:
    """
    Procura tokens que o Expo marcou como inválidos.
    O caso mais comum é DeviceNotRegistered.
    """
    invalid_tokens: list[str] = []

    for index, item in enumerate(expo_response_data):
        if index >= len(push_tokens):
            continue

        if item.get("status") != "error":
            continue

        details = item.get("details") or {}
        error_code = details.get("error")

        if error_code == "DeviceNotRegistered":
            invalid_tokens.append(push_tokens[index])

    return invalid_tokens


async def send_expo_push(
    db: Session,
    push_tokens: list[str],
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Envia push notification via Expo.
    - se o Expo identificar tokens inválidos, eles são desativados no banco
    - retorna um resumo do envio
    """
    if not push_tokens:
        return {
            "success": False,
            "message": "Nenhum token informado",
            "tickets": [],
            "invalid_tokens": [],
        }

    messages = [
        {
            "to": token,
            "title": title,
            "body": body,
            "sound": "default",
            "data": data or {},
        }
        for token in push_tokens
    ]

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                EXPO_PUSH_URL,
                json=messages,
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip, deflate",
                    "Content-Type": "application/json",
                },
            )

        response.raise_for_status()
        result = response.json()

        expo_data = result.get("data", [])
        invalid_tokens = _extract_invalid_tokens_from_expo_response(
            push_tokens=push_tokens,
            expo_response_data=expo_data,
        )

        if invalid_tokens:
            deactivate_invalid_tokens(db, invalid_tokens)

        return {
            "success": True,
            "message": "Push enviada com sucesso",
            "tickets": expo_data,
            "invalid_tokens": invalid_tokens,
        }

    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "message": f"Erro HTTP ao enviar push: {str(e)}",
            "tickets": [],
            "invalid_tokens": [],
        }

    except httpx.RequestError as e:
        return {
            "success": False,
            "message": f"Erro de conexão ao enviar push: {str(e)}",
            "tickets": [],
            "invalid_tokens": [],
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Erro inesperado ao enviar push: {str(e)}",
            "tickets": [],
            "invalid_tokens": [],
        }