from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from app.modules.audit.service import get_client_ip

LOGIN_RATE_LIMIT = "5/minute"
SIGNUP_RATE_LIMIT = "3/minute"
PASSWORD_RESET_REQUEST_RATE_LIMIT = "3/minute"
PASSWORD_RESET_CONFIRM_RATE_LIMIT = "3/minute"
INVITATION_CREATE_RATE_LIMIT = "10/minute"
INVITATION_SIGNUP_RATE_LIMIT = "5/minute"
LGPD_EXPORT_RATE_LIMIT = "2/hour"


def rate_limit_key_func(request: Request) -> str:
    client_ip = get_client_ip(request)
    return client_ip or "unknown-client"


limiter = Limiter(
    key_func=rate_limit_key_func,
    headers_enabled=True,
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests"},
    )
