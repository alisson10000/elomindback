import secrets
import hashlib


def generate_invite_token() -> str:
    """
    Gera token aleatório para convite (vai no link enviado por e-mail)
    """
    return secrets.token_urlsafe(32)


def hash_invite_token(token: str) -> str:
    """
    Gera hash SHA256 do token para salvar no banco
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
