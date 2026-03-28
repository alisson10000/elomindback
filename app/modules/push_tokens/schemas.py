from datetime import datetime
from pydantic import BaseModel, Field


class PushTokenCreate(BaseModel):
    expo_push_token: str = Field(..., min_length=8, max_length=255)
    platform: str | None = Field(default=None, max_length=20)


class PushTokenOut(BaseModel):
    id: int
    user_id: int
    expo_push_token: str
    platform: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PushTokenDeactivate(BaseModel):
    expo_push_token: str = Field(..., min_length=8, max_length=255)


class PushMessagePayload(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1, max_length=1000)
    data: dict | None = None