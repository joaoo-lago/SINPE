"""Protocolo Mestre/Específico e a árvore hierárquica de itens.

- Protocolo Mestre: árvore com todos os parâmetros clínicos possíveis.
- Protocolo Específico: subconjunto do mestre, focado numa patologia.
  Ele reaproveita os itens do mestre via SpecificProtocolItem (não duplica a árvore).
"""
from __future__ import annotations

import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ItemType, ProtocolKind, SelectionType


class Protocol(Base):
    __tablename__ = "protocols"

    kind: Mapped[ProtocolKind] = mapped_column(SAEnum(ProtocolKind))
    name: Mapped[str] = mapped_column(String(255))
    specialty: Mapped[str] = mapped_column(String(120), default="")
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Específico aponta para o mestre de origem; mestre tem NULL.
    parent_protocol_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("protocols.id"), nullable=True
    )

    items: Mapped[list["ProtocolItem"]] = relationship(
        back_populates="protocol", cascade="all, delete-orphan"
    )


class ProtocolItem(Base):
    """Nó da árvore. Raiz (item 'root') tem parent_item_id = NULL."""

    __tablename__ = "protocol_items"

    protocol_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("protocols.id"))
    parent_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("protocol_items.id"), nullable=True
    )
    # Caminho materializado (ex.: "root.anamnese.fatores_risco"). Em Postgres pode virar ltree.
    path: Mapped[str] = mapped_column(String(1024), default="")

    label: Mapped[str] = mapped_column(String(512))
    item_type: Mapped[ItemType] = mapped_column(SAEnum(ItemType), default=ItemType.LOGICAL)
    selection_type: Mapped[SelectionType] = mapped_column(
        SAEnum(SelectionType), default=SelectionType.SINGLE
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    # Controle de domínio para itens numéricos
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    min_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    protocol: Mapped["Protocol"] = relationship(back_populates="items")
    children: Mapped[list["ProtocolItem"]] = relationship(
        backref="parent", remote_side="ProtocolItem.parent_item_id", viewonly=True
    )


class SpecificProtocolItem(Base):
    """Liga um protocolo específico aos itens do mestre que o compõem."""

    __tablename__ = "specific_protocol_items"
    __table_args__ = (
        UniqueConstraint("specific_protocol_id", "master_item_id", name="uq_specific_item"),
    )

    specific_protocol_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("protocols.id"))
    master_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("protocol_items.id"))
    order_index: Mapped[int] = mapped_column(Integer, default=0)
