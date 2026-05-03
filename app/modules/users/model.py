from sqlalchemy import Boolean, Column, Enum, Integer, String, Text

from app.db.base_class import Base
from utils.security import decrypt_value, encrypt_value, hash_email, normalize_email


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email_hash = Column(String(64), unique=True, nullable=False, index=True)
    email_encrypted = Column(Text, nullable=False)
    name_encrypted = Column(Text, nullable=False)
    legacy_email = Column("email", String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    legacy_name = Column("name", String(255), nullable=True)
    role = Column(Enum("client", "therapist", name="user_role"), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    @property
    def email(self) -> str | None:
        if self.email_encrypted:
            return decrypt_value(self.email_encrypted)
        return self.legacy_email

    @email.setter
    def email(self, value: str) -> None:
        normalized = normalize_email(value)
        self.email_hash = hash_email(normalized)
        self.email_encrypted = encrypt_value(normalized)
        self.legacy_email = None

    @property
    def name(self) -> str | None:
        if self.name_encrypted:
            return decrypt_value(self.name_encrypted)
        return self.legacy_name

    @name.setter
    def name(self, value: str) -> None:
        clean_name = (value or "").strip()
        self.name_encrypted = encrypt_value(clean_name)
        self.legacy_name = None
