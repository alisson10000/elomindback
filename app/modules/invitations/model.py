from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from app.db.base import Base


class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(Integer, primary_key=True, index=True)
    therapist_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
