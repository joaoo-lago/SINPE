"""Transcrição de áudio da consulta e o resultado estruturado da IA."""
from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Transcription(Base):
    __tablename__ = "transcriptions"

    collection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collections.id"))
    audio_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)  # chave no storage
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)          # transcrição bruta
    structured: Mapped[dict | None] = mapped_column(JSONB, nullable=True)      # item_id -> valor
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    avg_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
