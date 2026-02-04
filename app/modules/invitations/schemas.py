from pydantic import BaseModel, EmailStr, Field

class InviteCreate(BaseModel):
    email: EmailStr

class InviteResponse(BaseModel):
    ok: bool
    email: EmailStr

class InviteValidateResponse(BaseModel):
    valid: bool
    email: EmailStr | None = None

class SignupFromInvite(BaseModel):
    token: str = Field(min_length=10)
    name: str = Field(min_length=2)
    password: str = Field(min_length=8)
