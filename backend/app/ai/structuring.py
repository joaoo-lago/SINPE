"""Estruturação por IA: transcrição da consulta -> valores dos itens do protocolo.

Fluxo (ver docs/ARQUITETURA.md §4):
  1. Áudio da consulta é transcrito por STT em nuvem (Whisper/Deepgram).
  2. O texto + o schema do Protocolo Específico vão para um LLM (Claude/GPT).
  3. O LLM responde em SAÍDA ESTRUTURADA: para cada item reconhecido, o valor + confiança.
  4. A coleta é PRÉ-preenchida; o profissional revisa e confirma antes de gravar.

Este módulo define o contrato e um stub. A chamada real ao provedor entra no Sprint 5,
com a chave injetada por ambiente (nunca commitada) e anonimização antes do envio.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ItemSchema:
    """O que o LLM precisa saber sobre cada item para preenchê-lo corretamente."""

    item_id: str
    label: str
    item_type: str          # logical | numeric | text | datetime | ...
    selection_type: str     # single | multiple
    allowed_children: list[str] | None = None  # rótulos das opções, quando aplicável


@dataclass
class StructuredValue:
    item_id: str
    value: Any
    confidence: float       # 0..1 — permite destacar baixa certeza na revisão


def build_prompt_schema(items: list[ItemSchema]) -> dict[str, Any]:
    """Monta a descrição do protocolo que vai no prompt/function-calling do LLM."""
    return {
        "instrucao": (
            "Você recebe a transcrição de uma consulta clínica. Preencha APENAS os itens "
            "explicitamente mencionados. Para cada item, devolva o valor no tipo correto e uma "
            "confiança de 0 a 1. Não invente dados não ditos."
        ),
        "itens": [
            {
                "item_id": it.item_id,
                "label": it.label,
                "tipo": it.item_type,
                "selecao": it.selection_type,
                "opcoes": it.allowed_children,
            }
            for it in items
        ],
    }


def structure_transcript(
    transcript: str,
    schema: list[ItemSchema],
) -> list[StructuredValue]:
    """Converte transcrição -> valores estruturados.

    STUB: implementação real (Sprint 5) chama o LLM com saída estruturada usando
    `build_prompt_schema(schema)` e faz o parse validando contra os tipos dos itens.
    """
    raise NotImplementedError(
        "Integração com LLM entra no Sprint 5. "
        "Use build_prompt_schema() para montar a chamada com saída estruturada."
    )
