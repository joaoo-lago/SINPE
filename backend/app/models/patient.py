"""Paciente. Obrigatórios: nome, sexo, raça (como no cadastro do SINPE).

Identificadores diretos (CPF/RG) devem ser cifrados em repouso — ver docs LGPD.
Aqui ficam como campos simples; a cifragem entra na camada de serviço (Sprint 2).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Patient(Base):
    __tablename__ = "patients"

    # Obrigatórios
    full_name: Mapped[str] = mapped_column(String(255))
    sex: Mapped[str] = mapped_column(String(20))          # masculino/feminino/indefinido
    race: Mapped[str] = mapped_column(String(50))

    # Opcionais
    occupation: Mapped[str | None] = mapped_column(String(120), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    national_id: Mapped[str | None] = mapped_column(String(64), nullable=True)   # RG (cifrar)
    tax_id: Mapped[str | None] = mapped_column(String(64), nullable=True)        # CPF (cifrar)
