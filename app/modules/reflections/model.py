from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class Reflection(Base):
    __tablename__ = "reflections"

    id = Column(Integer, primary_key=True, index=True)

    client_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    therapist_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    feeling_after_session = Column(Text, nullable=False)
    what_learned = Column(Text, nullable=False)
    positive_point = Column(Text, nullable=False)
    resistance_or_disagreement = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Cliente dono da reflexão
    client = relationship(
        "User",
        foreign_keys=[client_id],
        lazy="joined",
    )

    # Terapeuta vinculado à reflexão
    therapist = relationship(
        "User",
        foreign_keys=[therapist_id],
        lazy="joined",
    )
