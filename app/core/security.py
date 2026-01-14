from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from app.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES

def hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(raw: str, hashed: str) -> bool:
    return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))

def create_access_token(subject: str) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": subject, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
