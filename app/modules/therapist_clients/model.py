from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, Index, func
from app.db.base_class import Base


class TherapistClient(Base):
    __tablename__ = "therapist_clients"

    id = Column(Integer, primary_key=True)
    therapist_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, server_default=func.now())
    status = Column(String(30), nullable=False, default="active", server_default="active")
    ended_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_therapist_clients_status", "status"),
        Index("ix_therapist_clients_ended_at", "ended_at"),
        Index("ix_therapist_clients_client_status", "client_id", "status"),
    )
