from datetime import datetime
from pydantic import BaseModel


class FeedbackOut(BaseModel):
    id: int
    reflection_id: int
    ia_generated_content: str
    ia_neuro_nutrition_tip: str | None = None
    ia_activity_suggestion: str | None = None
    status: str
    therapist_approved_by: int | None = None
    therapist_notes: str | None = None

    approved_at: datetime | None = None
    created_at: datetime | None = None

    


class FeedbackApproveIn(BaseModel):
    ia_generated_content: str | None = None
    ia_neuro_nutrition_tip: str | None = None
    ia_activity_suggestion: str | None = None
    therapist_notes: str | None = None


class FeedbackRejectIn(BaseModel):
    therapist_notes: str | None = None


class FeedbackWithReflectionOut(BaseModel):
    # ===== Feedback (igual FeedbackOut) =====
    id: int
    reflection_id: int
    ia_generated_content: str
    ia_neuro_nutrition_tip: str | None = None
    ia_activity_suggestion: str | None = None
    status: str
    therapist_approved_by: int | None = None
    therapist_notes: str | None = None

    approved_at: datetime | None = None
    created_at: datetime | None = None

    # ===== Reflection (perguntas respondidas) =====
    client_id: int
    client_name: str | None = None  # se você tiver disponível (opcional)
    feeling_after_session: str
    what_learned: str
    positive_point: str
    resistance_or_disagreement: str | None = None
    reflection_created_at: datetime

    class Config:
        from_attributes = True
