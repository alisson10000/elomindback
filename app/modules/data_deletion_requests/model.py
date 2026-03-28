from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import relationship

from app.db.base import Base


class DataDeletionRequest(Base):
    __tablename__ = "data_deletion_requests"

    id = Column(Integer, primary_key=True, index=True)

    # ✅ importante: permitir SET NULL para manter o "audit" mesmo após apagar o user
    client_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # snapshot (para auditoria mínima mesmo após apagar o user)
    client_email = Column(String(255), nullable=True)
    client_name = Column(String(255), nullable=True)

    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # pending | completed | rejected | canceled (você decide no MVP)
    status = Column(String(30), nullable=False, server_default="pending")

    completed_at = Column(DateTime(timezone=True), nullable=True)

    client = relationship("User", foreign_keys=[client_id], lazy="joined")

    __table_args__ = (
        Index("ix_data_deletion_requests_client_status", "client_id", "status"),
    )
