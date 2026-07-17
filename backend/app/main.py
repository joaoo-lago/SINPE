"""Ponto de entrada da API do SINPE 2.0."""
from fastapi import FastAPI

from app.api import analysis
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Sistema Integrado de Protocolos Eletrônicos — pesquisa clínica e análise estatística.",
    version="0.1.0",
)

app.include_router(analysis.router)


@app.get("/health", tags=["infra"])
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "env": settings.environment}
