from datetime import datetime
from pydantic import BaseModel


# -------------------------
# CLIENT
# -------------------------
class DreamCreate(BaseModel):
    description: str


# Cliente não pode ver conteúdo após salvar:
# retorno mínimo
class DreamClientSavedOut(BaseModel):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# THERAPIST
# -------------------------
class DreamOut(BaseModel):
    id: int
    client_id: int
    therapist_id: int
    description: str
    therapist_tags: str | None = None
    therapist_notes: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DreamTherapistUpdate(BaseModel):
    therapist_tags: str | None = None
    therapist_notes: str | None = None
