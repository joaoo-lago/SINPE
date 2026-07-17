"""Modelos de domínio do SINPE.

Importar tudo aqui garante que o Alembic enxergue todas as tabelas.
"""
from app.models.enums import (
    CollectionSource,
    CollectionStatus,
    ItemType,
    ProtocolKind,
    SelectionType,
    UserRole,
)
from app.models.institution import Institution, User
from app.models.patient import Patient
from app.models.protocol import Protocol, ProtocolItem, SpecificProtocolItem
from app.models.collection import Collection, CollectionValue
from app.models.ai import Transcription

__all__ = [
    "CollectionSource",
    "CollectionStatus",
    "ItemType",
    "ProtocolKind",
    "SelectionType",
    "UserRole",
    "Institution",
    "User",
    "Patient",
    "Protocol",
    "ProtocolItem",
    "SpecificProtocolItem",
    "Collection",
    "CollectionValue",
    "Transcription",
]
