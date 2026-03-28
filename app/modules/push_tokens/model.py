from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, Boolean
from sqlalchemy.orm import relationship

from app.db.base import Base


class UserPushToken(Base):
    __tablename__ = "user_push_tokens"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    expo_push_token = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    platform = Column(String(20), nullable=True)

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )

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

    user = relationship("User", lazy="joined")