from pydantic import BaseModel

class ReflectionCreate(BaseModel):
    feeling_after_session: str
    what_learned: str
    positive_point: str
    resistance_or_disagreement: str | None = None

class ReflectionOut(BaseModel):
    id: int
    client_id: int
    feeling_after_session: str
    what_learned: str
    positive_point: str
    resistance_or_disagreement: str | None

    class Config:
        from_attributes = True
