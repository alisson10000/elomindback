from sqlalchemy import Column, Integer, ForeignKey, DateTime, func
from app.db.base_class import Base


class TherapistClient(Base):
    __tablename__ = "therapist_clients"

    id = Column(Integer, primary_key=True)
    therapist_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, server_default=func.now())
