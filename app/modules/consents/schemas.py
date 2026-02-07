from datetime import datetime
from pydantic import BaseModel


class ConsentOut(BaseModel):
    id: int
    client_id: int
    accepted_at: datetime

    class Config:
        from_attributes = True


class ConsentMeOut(BaseModel):
    accepted: bool
    accepted_at: datetime | None = None


class ConsentAcceptIn(BaseModel):
    accepted: bool = True
