"""Instituições e usuários (cadastros gerais do SINPE)."""
from __future__ import annotations

import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import UserRole


class Institution(Base):
    __tablename__ = "institutions"

    name: Mapped[str] = mapped_column(String(255))
    users: Mapped[list["User"]] = relationship(back_populates="institution")


class User(Base):
    __tablename__ = "users"

    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institutions.id"))
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole))

    institution: Mapped["Institution"] = relationship(back_populates="users")
