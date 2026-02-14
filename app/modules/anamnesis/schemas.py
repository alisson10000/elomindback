from datetime import datetime
from pydantic import BaseModel


class AnamnesisCreate(BaseModel):
    summary: str


class AnamnesisUpdate(BaseModel):
    summary: str


class AnamnesisOut(BaseModel):
    id: int
    client_id: int
    therapist_id: int
    summary: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
