# SINPE 2.0 — Arquitetura, Modelagem e Plano de Execução

> Reformulação moderna do **Sistema Integrado de Protocolos Eletrônicos** — de plataforma
> desktop C#/.NET (protocolo mestre/específico, coleta manual) para uma plataforma web de
> pesquisa clínica com **motor de busca e análise estatística** e **coleta automatizada por IA de voz**.
>
> Base documental: TCC "Criação de Protocolo Clínico para Pesquisa em Cardiologia" e o projeto
> PIBIC "Análise Comparativa entre uso de IA e coletas manuais" (FEMPAR / InCor Kubrusly).

## 0. Decisões de fundação (já tomadas)

| Eixo | Decisão | Motivo |
|------|---------|--------|
| Backend | **Python + FastAPI** | Um único backend serve API **e** motor estatístico (scipy/pandas/statsmodels) e integração de IA. |
| IA de voz | **APIs em nuvem** (transcrição + LLM estruturador) | Velocidade de desenvolvimento e acurácia; com consentimento e anonimização. |
| Escala | **Grupo de pesquisa** (centenas a poucos milhares de coletas) | Postgres bem modelado + DuckDB embutido resolve com custo quase zero. |
| Front-end | **React + TypeScript** | Ecossistema maduro para a árvore de protocolo, o construtor de queries e os gráficos. |

---

## 1. Stack tecnológico

### Visão em camadas

```
┌────────────────────────────────────────────────────────────────────┐
│  FRONT-END  — React + TypeScript + Vite                            │
│  • Editor da árvore do Protocolo Mestre (drag-and-drop)            │
│  • Construtor visual de coletas (Protocolo Específico)            │
│  • Query Builder: cruzar dezenas de variáveis                     │
│  • Dashboards: gráficos (barra, pizza) + tabelas de testes        │
│  • Gravador de áudio da consulta (Web Audio API + WebSocket)      │
│    Libs: TanStack Query, Recharts/ECharts, react-hook-form        │
└──────────────┬─────────────────────────────────────────────────────┘
               │ HTTPS / WebSocket (streaming de áudio e transcrição)
┌──────────────▼─────────────────────────────────────────────────────┐
│  BACK-END  — Python 3.12 + FastAPI (Uvicorn/Gunicorn)             │
│  ┌────────────────┐ ┌──────────────────┐ ┌─────────────────────┐  │
│  │ API de domínio │ │ Motor estatístico│ │ Serviço de IA       │  │
│  │ protocolos,    │ │ scipy/statsmodels│ │ transcrição +       │  │
│  │ pacientes,     │ │ + pandas + DuckDB│ │ LLM estruturador    │  │
│  │ coletas, auth  │ │                  │ │ (fila assíncrona)   │  │
│  └────────┬───────┘ └────────┬─────────┘ └─────────┬───────────┘  │
└───────────┼──────────────────┼─────────────────────┼──────────────┘
            │                  │                     │
┌───────────▼──────────┐ ┌─────▼────────────┐ ┌──────▼─────────────┐
│ PostgreSQL 16 (OLTP) │ │ DuckDB / views   │ │ Celery + Redis     │
│ verdade transacional │ │ materializadas   │ │ (jobs de IA/áudio) │
│ + JSONB + índices    │ │ (OLAP analítico) │ │                    │
└──────────────────────┘ └──────────────────┘ └────────────────────┘
            │                                          │
      ┌─────▼──────┐                          ┌────────▼──────────┐
      │ Object     │                          │ APIs de IA nuvem  │
      │ storage    │                          │ • Speech-to-text  │
      │ (S3/MinIO) │                          │   (Whisper/Deepgram)│
      │ áudio+mídia│                          │ • LLM estruturador│
      └────────────┘                          │   (Claude/GPT)    │
                                              └───────────────────┘
```

### Componentes e justificativa

| Camada | Tecnologia | Por quê |
|--------|-----------|---------|
| **Front-end** | React + TypeScript + Vite | Tipagem forte para a estrutura hierárquica; ecossistema de componentes. |
| **Gráficos** | Recharts (padrão) ou ECharts (volumes maiores) | Barra e pizza saem prontos; tabelas de teste renderizadas ao lado. |
| **API** | FastAPI + Pydantic v2 | Async nativo (crucial para streaming de áudio), validação forte, OpenAPI automático. |
| **ORM** | SQLAlchemy 2.0 + Alembic | Modelagem da árvore + migrações versionadas. |
| **OLTP** | PostgreSQL 16 | Verdade transacional, integridade referencial, JSONB, `ltree` para hierarquia. |
| **OLAP** | DuckDB (embutido) lendo do Postgres | Análises colunar/vetorizadas *super rápidas* para cruzar dezenas de variáveis, sem servidor extra. |
| **Estatística** | pandas, numpy, scipy.stats, statsmodels, pingouin | Qui-quadrado, t-Student, ANOVA, correlação, regressão — tudo no backend. |
| **Fila** | Celery + Redis | Transcrição e estruturação por IA rodam fora do request. |
| **IA voz** | Whisper/Deepgram (STT) + Claude/GPT (estruturação) | STT em tempo real; LLM mapeia texto → itens do protocolo. |
| **Storage** | MinIO (dev) / S3 (prod) | Áudio das consultas e mídia dos itens (imagens, sons, vídeos). |
| **Auth** | OAuth2 + JWT (FastAPI Security) | Papéis: Administrador, Visualizador, Coletor, Pesquisador. |

---

## 2. Modelagem do banco (OLTP + OLAP híbrido)

### 2.1 O problema central

O SINPE legado é, na essência, um sistema **EAV (Entity-Attribute-Value)**: o Protocolo Mestre é uma
árvore de "atributos possíveis"; cada coleta grava um subconjunto de valores. Isso dá flexibilidade
infinita (qualquer especialidade, qualquer variável) mas é **péssimo para query analítica** se ingênuo.

A solução é **híbrida**:

- **OLTP normalizado** (Postgres) → escrita, integridade, rastreabilidade da coleta.
- **Camada OLAP derivada** (DuckDB + views materializadas) → leitura analítica rápida, pivotando o EAV
  em formato largo (uma coluna por variável) sob demanda.

### 2.2 Esquema relacional (OLTP)

```
institutions ──< users
                   │
patients ──< collections >── protocols (mestre/específico, self-ref)
                   │              │
                   │         protocol_items (árvore: parent_item_id)
                   │              │
             collection_values ──┘   (EAV: 1 linha por item coletado)
                   │
             media_assets, transcriptions, audit_log
```

**`protocols`** — mestre e específico na mesma tabela:
| coluna | tipo | nota |
|--------|------|------|
| id | UUID PK | |
| kind | enum(`master`,`specific`) | |
| parent_protocol_id | UUID FK → protocols | específico aponta para o mestre de origem |
| name, specialty | text | ex.: "Cardiologia", "Infarto Agudo do Miocárdio" |
| version | int | versionamento do protocolo |

**`protocol_items`** — a árvore hierárquica (o "eixo root" e seus filhos):
| coluna | tipo | nota |
|--------|------|------|
| id | UUID PK | |
| protocol_id | UUID FK | |
| parent_item_id | UUID FK → protocol_items (self) | raiz = NULL |
| path | `ltree` | caminho materializado p/ subárvore rápida |
| label | text | descrição do item |
| item_type | enum | `logical`, `numeric`, `text`, `datetime`, `image`, `sound`, `video` |
| selection_type | enum(`single`,`multiple`) | única ou múltipla seleção |
| unit, min_value, max_value | | controle de domínio p/ numéricos |
| order_index | int | ordem entre irmãos |

**`specific_protocol_items`** — quais itens do mestre compõem um específico
(o específico é um *subconjunto* selecionado do mestre):
`(specific_protocol_id, master_item_id)`.

**`patients`** — obrigatórios: nome, sexo, raça; opcionais: profissão, nascimento, RG, CPF, doc.
> ⚠️ Dado sensível de saúde (LGPD): identificadores diretos ficam **cifrados em repouso** e separados
> dos dados clínicos para permitir análise anonimizada.

**`collections`** — a coleta/encontro:
`patient_id, protocol_id (específico), collector_id, started_at, finished_at, status, source(manual|ai)`.

**`collection_values`** — o coração EAV, uma linha por item marcado na coleta:
| coluna | tipo |
|--------|------|
| collection_id, item_id | FK |
| value_bool, value_numeric, value_text, value_date | tipados (só um preenchido) |
| value_json | JSONB (multiseleção/estruturas) |
| source | `manual` \| `ai` |
| confidence | float (quando veio da IA) |

**Cadastros e trilha:** `institutions`, `users(role)`, `media_assets`, `audit_log`
(rastreamento de quem coletou — requisito do SINPE), `transcriptions`.

### 2.3 A camada analítica (OLAP) — por que resolve o "cruzar dezenas de variáveis"

O cruzamento tipo *"infarto agudo do miocárdio, < 30 anos, usando fármaco X"* é uma consulta
que toca muitas variáveis EAV ao mesmo tempo. Duas técnicas:

1. **Views materializadas por protocolo** — pivotam o EAV em uma tabela larga
   (`v_cardiologia_wide`: uma coluna por item do protocolo), atualizadas incrementalmente.
2. **DuckDB embutido** — lê o Postgres (extensão `postgres_scanner`) e roda a query analítica
   em memória colunar. Para milhares de coletas × dezenas de variáveis, respostas em milissegundos
   sem infra extra. Quando/se escalar para nacional, troca-se DuckDB por ClickHouse sem tocar no OLTP.

```
Coleta grava → collection_values (EAV, Postgres OLTP)
                        │  (refresh incremental)
                        ▼
             view materializada larga  ←── DuckDB roda cruzamentos + agрega
                        │
                        ▼
          motor estatístico (pandas DataFrame) → gráficos + testes
```

---

## 3. Motor estatístico e gráficos

**Regra de ouro: a matemática mora no Python (back-end); o front-end só desenha.**

### 3.1 Fluxo

```
Query Builder (front) ── JSON de filtros ──▶ /api/analysis/run
                                                   │
   1. QueryBuilder traduz filtros → SQL/DuckDB     │
   2. Executa → pandas DataFrame                   │
   3. StatsEngine escolhe o teste certo:           │
        • 2 categóricas  → Qui-quadrado / Fisher   │
        • categórica × numérica (2 grupos) → t-Student
        • categórica × numérica (3+)  → ANOVA      │
        • numérica × numérica → Pearson/Spearman   │
   4. Gera séries de gráfico (barra/pizza)         │
                                                   ▼
   Retorno JSON: { chart_data, statistic, p_value, effect_size, interpretação }
                                                   │
                              Recharts desenha ◀───┘
```

### 3.2 Bibliotecas

| Tarefa | Biblioteca |
|--------|-----------|
| Manipulação | pandas, numpy |
| Testes de hipótese | scipy.stats (`chi2_contingency`, `ttest_ind`, `f_oneway`, `pearsonr`) |
| Modelos/ANOVA/regressão | statsmodels |
| Conveniência + tamanho de efeito | pingouin |
| Descritivas | pandas `.describe()`, frequências |

### 3.3 Seleção automática do teste

O back-end inspeciona o tipo de cada variável (`item_type`) e a cardinalidade dos grupos e
**escolhe o teste apropriado automaticamente** — o pesquisador só arrasta as variáveis. Isso
replica e supera o "analisador" do SINPE legado (que já fazia t-Student e qui-quadrado), mas
com validação de pressupostos (normalidade via Shapiro, homocedasticidade via Levene) e
alerta quando o teste paramétrico não é adequado (cai para Mann-Whitney/Kruskal-Wallis).

---

## 4. Automação por IA (voz → protocolo)

```
Consulta (áudio médico+paciente)
   │  WebSocket streaming
   ▼
STT em tempo real (Whisper/Deepgram) ──▶ transcrição parcial no front
   │  (ao finalizar)
   ▼
LLM estruturador (Claude/GPT) recebe:
   • transcrição completa
   • o schema do Protocolo Específico (itens + tipos + domínios)
   └─▶ devolve JSON: { item_id: valor, confidence } para cada item reconhecido
   │
   ▼
Pré-preenchimento da coleta ──▶ médico revisa/confirma ──▶ grava em collection_values
                                     (source='ai', confidence registrada)
```

Pontos-chave:
- **Function calling / saída estruturada** força o LLM a responder no formato exato do protocolo.
- **Nada é gravado sem revisão humana** — a IA pré-preenche, o profissional confirma (rastreabilidade).
- `confidence` por campo permite destacar o que a IA teve baixa certeza.
- Estudo PIBIC pede comparação IA × manual → registramos `source`, `tempo_de_coleta` e correções
  para medir tempo/acurácia (métricas que o próprio projeto quer avaliar).
- **LGPD/CEP:** consentimento explícito, anonimização antes de enviar ao LLM, contrato/BAA com o provedor.

---

## 5. Plano de execução (MVP em sprints)

Sprints de ~2 semanas. A ordem entrega valor cedo: **primeiro o núcleo de protocolos e coleta manual
(replica o SINPE), depois análise, por fim a IA** (que é o diferencial do PIBIC).

### Sprint 0 — Fundação (infra)
- [ ] Repositório, Docker Compose (Postgres + Redis + MinIO), CI básico.
- [ ] Esqueleto FastAPI + SQLAlchemy + Alembic; healthcheck.
- [ ] Auth OAuth2/JWT com os 4 papéis; cadastro de instituição e usuário.
- **Entregue neste scaffold.** ✅

### Sprint 1 — Protocolo Mestre (a árvore)
- [ ] Modelos `protocols` + `protocol_items` (self-ref + `ltree`).
- [ ] API CRUD de itens: adicionar irmão / adicionar filho, tipo, seleção única/múltipla.
- [ ] Front: editor de árvore drag-and-drop.
- **Meta:** recriar o "eixo root" e ramificar itens como no SINPE.

### Sprint 2 — Protocolo Específico + Pacientes
- [ ] Seleção de itens do mestre para compor específicos (ex.: IAM, HAS, IC…).
- [ ] Cadastro de pacientes (obrigatórios/opcionais + cifragem de identificadores).

### Sprint 3 — Coleta manual
- [ ] `collections` + `collection_values` (EAV).
- [ ] Front: abrir protocolo específico, marcar itens, "finalizar coleta".
- **Meta:** paridade funcional com o SINPE desktop (coleta 100% manual funcionando).

### Sprint 4 — Motor estatístico + gráficos
- [ ] View materializada larga + DuckDB.
- [ ] `StatsEngine` (qui-quadrado, t-Student, ANOVA, correlação) com seleção automática.
- [ ] Query Builder no front + gráficos barra/pizza + tabela de teste.
- **Meta:** reproduzir os gráficos do TCC (sexo, faixa etária, diagnóstico, fármacos) automaticamente.

### Sprint 5 — Coleta por IA (voz)
- [ ] Captura/streaming de áudio (WebSocket) + STT.
- [ ] LLM estruturador com saída no schema do específico.
- [ ] Fila Celery + tela de revisão humana + registro de `confidence`/`source`.

### Sprint 6 — Estudo comparativo (PIBIC) + hardening
- [ ] Métricas IA × manual: tempo de coleta, taxa de correção, acurácia.
- [ ] Exportação de dados (CSV/relatório) e auditoria completa.
- [ ] Revisão LGPD/CEP, testes, deploy.

---

## 6. Riscos e cuidados

| Risco | Mitigação |
|-------|-----------|
| EAV lento em análise | Camada OLAP (DuckDB + views largas) desde o Sprint 4. |
| Dado sensível de saúde | Cifragem em repouso, anonimização antes do LLM, trilha de auditoria. |
| IA "alucinar" valores | Saída estruturada + revisão humana obrigatória + confidence por campo. |
| Propriedade intelectual do SINPE© | Reimplementação própria; validar autorização de uso (Anexo 1 dos documentos). |
| Custo de API de IA | Anonimização + envio só do texto necessário; medir tokens. |
```
