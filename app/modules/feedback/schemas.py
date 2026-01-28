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

    class Config:
        from_attributes = True


class FeedbackApproveIn(BaseModel):
    ia_generated_content: str | None = None
    ia_neuro_nutrition_tip: str | None = None
    ia_activity_suggestion: str | None = None
    therapist_notes: str | None = None


class FeedbackRejectIn(BaseModel):
    therapist_notes: str | None = None
