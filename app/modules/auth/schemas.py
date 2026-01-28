from pydantic import BaseModel, EmailStr

class SignupIn(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: str  # "client" | "therapist" (MVP)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ✅ NOVO: retorno do /auth/me
class MeOut(BaseModel):
    id: int
    email: EmailStr
    name: str
    role: str

    class Config:
        from_attributes = True
