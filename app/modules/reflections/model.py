from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Reflection(Base):
    __tablename__ = "reflections"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    feeling_after_session = Column(Text, nullable=False)
    what_learned = Column(Text, nullable=False)
    positive_point = Column(Text, nullable=False)
    resistance_or_disagreement = Column(Text, nullable=True)

    client = relationship("User")
