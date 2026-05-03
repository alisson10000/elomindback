from sqlalchemy import Column, Integer, Text, String, Enum, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base_class import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)

    reflection_id = Column(
        Integer,
        ForeignKey("reflections.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    ia_generated_content = Column(Text, nullable=False)
    ia_neuro_nutrition_tip = Column(String(500), nullable=True)
    ia_activity_suggestion = Column(String(500), nullable=True)

    status = Column(
        Enum("pending_approval", "approved", "rejected", name="feedback_status"),
        nullable=False,
        default="pending_approval",
        index=True,
    )

    therapist_approved_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )

    therapist_notes = Column(Text, nullable=True)

    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    reflection = relationship("Reflection", lazy="joined")
    approved_by = relationship("User", foreign_keys=[therapist_approved_by], lazy="joined")
