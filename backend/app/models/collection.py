"""Coleta (encontro clínico) e seus valores em modelo EAV.

Cada coleta grava um subconjunto de itens do protocolo específico.
CollectionValue = 1 linha por item marcado (Entity-Attribute-Value).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import CollectionSource, CollectionStatus


class Collection(Base):
    __tablename__ = "collections"

    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("patients.id"))
    protocol_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("protocols.id"))  # específico
    collector_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))

    status: Mapped[CollectionStatus] = mapped_column(
        SAEnum(CollectionStatus), default=CollectionStatus.DRAFT
    )
    source: Mapped[CollectionSource] = mapped_column(
        SAEnum(CollectionSource), default=CollectionSource.MANUAL
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    values: Mapped[list["CollectionValue"]] = relationship(
        back_populates="collection", cascade="all, delete-orphan"
    )


class CollectionValue(Base):
    """Valor EAV: só uma das colunas value_* é preenchida, conforme item_type."""

    __tablename__ = "collection_values"

    collection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collections.id"))
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("protocol_items.id"))

    value_bool: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    value_numeric: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    value_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # multiseleção

    source: Mapped[CollectionSource] = mapped_column(
        SAEnum(CollectionSource), default=CollectionSource.MANUAL
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)  # quando veio de IA

    collection: Mapped["Collection"] = relationship(back_populates="values")
