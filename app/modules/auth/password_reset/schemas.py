from pydantic import BaseModel, EmailStr, Field


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ForgotPasswordOut(BaseModel):
    ok: bool = True


class ResetPasswordIn(BaseModel):
    email: EmailStr
    token: str = Field(..., min_length=4, max_length=128)  # código 6 dígitos ou token
    password: str = Field(..., min_length=8)


class ResetPasswordOut(BaseModel):
    ok: bool = True
