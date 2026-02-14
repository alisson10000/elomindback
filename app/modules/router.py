from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, func, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class Anamnesis(Base):
    __tablename__ = "anamnesis"

    id = Column(Integer, primary_key=True, index=True)

    client_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    therapist_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    summary = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # garante 1 anamnese por (cliente, terapeuta)
    __table_args__ = (
        UniqueConstraint("client_id", "therapist_id", name="uq_anamnesis_client_therapist"),
    )

    # relações opcionais (mantém consistente com seu Reflection.model, sem exigir back_populates no User)
    client = relationship("User", foreign_keys=[client_id], lazy="joined")
    therapist = relationship("User", foreign_keys=[therapist_id], lazy="joined")
