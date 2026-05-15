from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ExportProfileOut(BaseModel):
    id: int
    email: str | None
    name: str | None
    role: str
    is_active: bool


class ExportConsentOut(BaseModel):
    consent_version: str | None = None
    accepted_at: datetime


class ExportReflectionOut(BaseModel):
    id: int
    feeling_after_session: str | None
    what_learned: str | None
    positive_point: str | None
    resistance_or_disagreement: str | None
    created_at: datetime
    updated_at: datetime


class ExportFeedbackOut(BaseModel):
    id: int
    reflection_id: int
    ia_generated_content: str | None
    ia_neuro_nutrition_tip: str | None
    ia_activity_suggestion: str | None
    status: str
    approved_at: datetime | None
    created_at: datetime


class ExportDreamOut(BaseModel):
    id: int
    description: str | None
    therapist_tags: str | None
    therapist_notes: str | None
    created_at: datetime
    updated_at: datetime


class DataExportOut(BaseModel):
    profile: ExportProfileOut
    consents: list[ExportConsentOut]
    reflections: list[ExportReflectionOut]
    feedbacks: list[ExportFeedbackOut]
    dreams: list[ExportDreamOut]
