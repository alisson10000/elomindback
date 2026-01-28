from pydantic import BaseModel, EmailStr

class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class UserStatusUpdate(BaseModel):
    is_active: bool
