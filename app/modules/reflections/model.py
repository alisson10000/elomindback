from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Reflection(Base):
    __tablename__ = "reflections"

    id = Column(Integer, primary_key=True, index=True)

    client_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
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

    # ✅ Ajuste: remove back_populates para não exigir User.reflections
    client = relationship(
        "User",
        lazy="joined",
    )
