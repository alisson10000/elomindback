from sqlalchemy import Column, Integer, ForeignKey, DateTime, func
from app.db.base_class import Base

class Consent(Base):
    __tablename__ = "consents"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    accepted_at = Column(DateTime, server_default=func.now(), nullable=False)
