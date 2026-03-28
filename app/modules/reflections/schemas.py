from datetime import datetime
from pydantic import BaseModel


class ReflectionCreate(BaseModel):
    feeling_after_session: str
    what_learned: str
    positive_point: str
    resistance_or_disagreement: str | None = None


# usado no PATCH /reflections/{id}
class ReflectionUpdate(BaseModel):
    feeling_after_session: str
    what_learned: str
    positive_point: str
    resistance_or_disagreement: str | None = None


# usado no POST /reflections
class ReflectionOut(BaseModel):
    id: int
    client_id: int
    therapist_id: int | None = None
    feeling_after_session: str
    what_learned: str
    positive_point: str
    resistance_or_disagreement: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# usado no GET /reflections/me
class ReflectionOutWithFlags(ReflectionOut):
    can_delete: bool

    class Config:
        from_attributes = True


# THERAPIST - lista pendentes
class ReflectionPendingOut(BaseModel):
    id: int
    client_id: int
    therapist_id: int | None = None
    client_name: str
    feeling_after_session: str
    created_at: datetime

    class Config:
        from_attributes = True


# THERAPIST - detalhe
class ReflectionDetailOut(BaseModel):
    id: int
    client_id: int
    therapist_id: int | None = None
    client_name: str
    feeling_after_session: str
    what_learned: str
    positive_point: str
    resistance_or_disagreement: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True