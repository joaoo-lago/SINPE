"""Configuração central da aplicação (12-factor: tudo por variável de ambiente)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SINPE_", extra="ignore")

    app_name: str = "SINPE 2.0"
    environment: str = "dev"

    # Postgres (OLTP)
    database_url: str = "postgresql+psycopg://sinpe:sinpe@localhost:5432/sinpe"

    # Redis (fila Celery)
    redis_url: str = "redis://localhost:6379/0"

    # Segurança
    jwt_secret: str = "troque-em-producao"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 60

    # IA em nuvem (transcrição + estruturação)
    stt_provider: str = "whisper"          # whisper | deepgram
    llm_provider: str = "claude"           # claude | openai
    llm_api_key: str = ""                  # injetada por env; nunca commitada


@lru_cache
def get_settings() -> Settings:
    return Settings()
