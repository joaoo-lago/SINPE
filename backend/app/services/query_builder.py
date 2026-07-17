"""Construtor de queries analíticas — o motor de busca do SINPE.

Traduz filtros de cruzamento de variáveis (ex.: "IAM + idade < 30 + fármaco X")
em uma consulta sobre os dados EAV e devolve um DataFrame em formato LARGO
(uma coluna por item do protocolo) pronto para o motor estatístico.

Estratégia de performance (ver docs/ARQUITETURA.md §2.3):
  - Protótipo: pivota o EAV com pandas (suficiente p/ escala de grupo de pesquisa).
  - Produção: DuckDB lê a view materializada larga e faz o cruzamento vetorizado.

Este módulo isola essa decisão: a API chama `build_wide_frame(...)` e não sabe
se por baixo é pandas ou DuckDB.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Collection, CollectionValue, ProtocolItem

Operator = Literal["eq", "neq", "lt", "lte", "gt", "gte", "in", "is_true"]


@dataclass
class Filter:
    """Um filtro sobre um item do protocolo (uma variável)."""

    item_id: str
    operator: Operator
    value: Any = None


def _value_of(cv: CollectionValue) -> Any:
    """Extrai o valor tipado de uma linha EAV."""
    for attr in ("value_bool", "value_numeric", "value_text", "value_date"):
        v = getattr(cv, attr)
        if v is not None:
            return v
    return cv.value_json


def build_wide_frame(
    db: Session,
    protocol_id: str,
    item_ids: list[str],
) -> pd.DataFrame:
    """Monta o DataFrame largo: uma linha por coleta, uma coluna por item pedido.

    Rótulo da coluna = label do item (legível para o pesquisador).
    """
    labels = {
        str(i.id): i.label
        for i in db.execute(
            select(ProtocolItem).where(ProtocolItem.id.in_(item_ids))
        ).scalars()
    }

    rows: dict[str, dict[str, Any]] = {}
    stmt = (
        select(CollectionValue, Collection.id)
        .join(Collection, CollectionValue.collection_id == Collection.id)
        .where(Collection.protocol_id == protocol_id)
        .where(CollectionValue.item_id.in_(item_ids))
    )
    for cv, collection_id in db.execute(stmt).all():
        key = str(collection_id)
        rows.setdefault(key, {})
        col = labels.get(str(cv.item_id), str(cv.item_id))
        rows[key][col] = _value_of(cv)

    return pd.DataFrame.from_dict(rows, orient="index").reset_index(drop=True)


def apply_filters(df: pd.DataFrame, filters: list[Filter], label_map: dict[str, str]) -> pd.DataFrame:
    """Aplica os filtros de cruzamento sobre o DataFrame largo."""
    out = df
    for f in filters:
        col = label_map.get(f.item_id, f.item_id)
        if col not in out.columns:
            continue
        s = out[col]
        if f.operator == "eq":
            out = out[s == f.value]
        elif f.operator == "neq":
            out = out[s != f.value]
        elif f.operator == "lt":
            out = out[s < f.value]
        elif f.operator == "lte":
            out = out[s <= f.value]
        elif f.operator == "gt":
            out = out[s > f.value]
        elif f.operator == "gte":
            out = out[s >= f.value]
        elif f.operator == "in":
            out = out[s.isin(f.value)]
        elif f.operator == "is_true":
            out = out[s == True]  # noqa: E712
    return out
