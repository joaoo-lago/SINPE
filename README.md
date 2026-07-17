# SINPE 2.0

Reformulação moderna do **Sistema Integrado de Protocolos Eletrônicos** — plataforma web de
pesquisa clínica com protocolos Mestre/Específico, **motor de busca e análise estatística** e
**coleta automatizada por IA de voz**.

> Base: TCC "Criação de Protocolo Clínico para Pesquisa em Cardiologia" + projeto PIBIC
> (FEMPAR / InCor Kubrusly). Arquitetura completa em [`docs/ARQUITETURA.md`](docs/ARQUITETURA.md).

## Stack

- **Backend:** Python 3.12 + FastAPI + SQLAlchemy 2.0
- **OLTP:** PostgreSQL 16 (verdade transacional, EAV das coletas)
- **OLAP:** DuckDB + views materializadas (cruzamento rápido de dezenas de variáveis)
- **Estatística:** scipy / statsmodels / pandas / pingouin (no backend)
- **IA de voz:** STT em nuvem (Whisper/Deepgram) + LLM estruturador (Claude/GPT)
- **Front-end:** React + TypeScript (a construir)

## O que já está nesta fundação

```
sinpe/
├── docs/ARQUITETURA.md         # arquitetura, modelagem de banco, plano de sprints
├── docker-compose.yml          # Postgres + Redis + MinIO
└── backend/
    ├── app/
    │   ├── models/             # Protocolo Mestre/Específico, árvore de itens, coleta EAV
    │   ├── stats/engine.py     # motor estatístico com seleção automática de teste ✅ testado
    │   ├── services/query_builder.py  # pivota EAV -> formato largo (motor de busca)
    │   ├── ai/structuring.py   # contrato transcrição -> itens do protocolo
    │   ├── api/analysis.py     # POST /api/analysis/run (cruza variáveis, roda o teste)
    │   └── main.py
    └── tests/test_stats_engine.py     # prova que qui-quadrado, t-Student e correlação funcionam
```

## Rodar o backend

```bash
# 1. Subir infra
docker compose up -d

# 2. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # ajuste a chave da IA quando for usar o Sprint 5

# 3. Rodar os testes do motor estatístico
pytest

# 4. Subir a API
uvicorn app.main:app --reload
# docs interativas em http://localhost:8000/docs
```

## Próximos passos (ver `docs/ARQUITETURA.md` §5)

- **Sprint 1:** editor da árvore do Protocolo Mestre (API + front drag-and-drop)
- **Sprint 2:** Protocolo Específico + cadastro de pacientes
- **Sprint 3:** coleta manual (paridade com o SINPE desktop)
- **Sprint 4:** motor estatístico ligado ao Query Builder no front + gráficos
- **Sprint 5:** coleta por IA de voz
- **Sprint 6:** estudo comparativo IA × manual (PIBIC) + hardening/LGPD
