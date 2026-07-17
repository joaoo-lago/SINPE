"""Endpoint de análise: recebe filtros de cruzamento, roda o teste e devolve gráfico + resultado.

Amarra query_builder (monta o formato largo) + stats.engine (escolhe e roda o teste).
"""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.services import query_builder as qb
from app.stats import engine as stats

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


class FilterIn(BaseModel):
    item_id: str
    operator: Literal["eq", "neq", "lt", "lte", "gt", "gte", "in", "is_true"]
    value: Any = None


class AnalysisRequest(BaseModel):
    protocol_id: str
    var_x_item_id: str
    var_y_item_id: str
    filters: list[FilterIn] = []
    kind_x: Literal["categorical", "numeric"] | None = None
    kind_y: Literal["categorical", "numeric"] | None = None


@router.post("/run")
def run_analysis(req: AnalysisRequest, db: Session = Depends(get_db)) -> dict:
    item_ids = list({req.var_x_item_id, req.var_y_item_id, *[f.item_id for f in req.filters]})

    df = qb.build_wide_frame(db, req.protocol_id, item_ids)

    # rótulos: build_wide_frame já usa label como nome de coluna; para filtrar precisamos do mapa
    from app.models import ProtocolItem  # import local p/ evitar ciclo
    from sqlalchemy import select

    label_map = {
        str(i.id): i.label
        for i in db.execute(select(ProtocolItem).where(ProtocolItem.id.in_(item_ids))).scalars()
    }

    df = qb.apply_filters(
        df,
        [qb.Filter(f.item_id, f.operator, f.value) for f in req.filters],
        label_map,
    )

    if df.empty:
        return {"empty": True, "message": "Nenhuma coleta atende aos filtros."}

    col_x = label_map.get(req.var_x_item_id, req.var_x_item_id)
    col_y = label_map.get(req.var_y_item_id, req.var_y_item_id)
    result = stats.analyze(df, col_x, col_y, req.kind_x, req.kind_y)

    return {
        "empty": False,
        "n": len(df),
        "chart": result.chart.__dict__,
        "test": result.test.__dict__ if result.test else None,
    }
