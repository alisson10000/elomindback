from datetime import datetime
from pydantic import BaseModel


class DataDeletionRequestOut(BaseModel):
    id: int
    client_id: int | None = None
    client_email: str | None = None
    client_name: str | None = None
    requested_at: datetime
    status: str
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class DataDeletionRequestCreateOut(BaseModel):
    id: int
    requested_at: datetime
    status: str

    class Config:
        from_attributes = True
