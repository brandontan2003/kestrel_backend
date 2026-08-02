# Kestrel — Backend

> Thesis-driven stock monitoring. Define your investment conditions, Kestrel watches the market and tells you when they're met.

**Frontend repo →** [kestrel-frontend](https://github.com/jiahuiiiii/Kestrel)

---

## What it does

Most alerting tools send you a ping when a price hits a number. Kestrel lets you encode a full investment thesis — *"I want NVDA under 28 P/E **and** a hyperscaler capex cut **and** data-center revenue decel"* — and only alerts you when all of it is true simultaneously.

Two types of conditions per thesis:

- **Quantitative** — deterministic threshold checks (P/E, P/B, EV/EBITDA, price vs. 200-day MA) pulled from `yfinance`.
- **Qualitative (catalysts)** — event-based triggers evaluated by a two-pass LLM classifier scanning live news: Haiku filters for relevance, Sonnet confirms and must cite a supporting quote or the result is rejected.

The system **never trades**. It surfaces signal; you decide.

---

## Architecture

```
kestrel-backend/
├── app/
│   ├── api/v1/              # REST endpoints (theses, proposals, alerts, auth, etc.)
│   ├── core/
│   │   ├── authorization/   # JWT auth (access + refresh, HttpOnly cookies)
│   │   └── database/        # Audit hooks (sqlalchemy-history)
│   ├── dto/                 # Pydantic v2 request/response schemas
│   ├── enums/               # Domain enums
│   ├── models/              # SQLAlchemy ORM models (schema source of truth)
│   ├── repository/          # DB access layer (flush only, never commit)
│   ├── service/             # Business logic (no SQLAlchemy imports)
│   ├── websocket/           # WebSocket connection manager + push handler
│   ├── config.py            # Pydantic settings (env-file backed)
│   ├── database_registry.py # Async engine init
│   ├── database_dependency.py # get_db FastAPI dependency
│   ├── exception_handler.py # Global error → HTTP response mapping
│   └── main.py              # App factory, lifespan, middleware, router mount
├── pipeline/                # Vendored ML pipeline (news fetch + LLM classifier)
│   ├── news.py              # Finnhub + yfinance news adapters with dedup
│   ├── llm.py               # Two-pass classifier (Haiku → Sonnet)
│   ├── evaluator.py         # Quant + catalyst signal aggregation
│   ├── proposals.py         # LLM-driven thesis change suggestions
│   ├── catalysts.py
│   ├── prompts/             # Prompt templates (pass1, pass2, propose_changes)
│   └── run.py               # CLI spike driver for pipeline testing
├── common/                  # Shared enums package (installed as editable dep)
│   └── enums/               # AlertsEnum, CatalystEnum, ProposalEnum, ThesesEnum
├── db_migration/            # Flyway SQL migrations (V1.0 → V1.11)
├── tests/
│   ├── unit/                # Service-layer unit tests (mocked repos)
│   ├── integration/         # Controller integration tests (TestClient + aiosqlite)
│   └── enums/               # Enum contract tests
├── docker-compose.yml       # postgres + flyway + backend (local dev)
├── Dockerfile
├── requirements.txt
└── pytest.ini
```

---

## Stack

| Layer              | Technology                                                     |
|--------------------|----------------------------------------------------------------|
| Runtime            | Python 3.12                                                    |
| Web framework      | FastAPI 0.138 + Uvicorn                                        |
| ORM                | SQLAlchemy 2.0 (async)                                         |
| Database           | PostgreSQL 17 (Docker locally, Railway in production)          |
| Migrations         | Flyway 12.7                                                    |
| Auth               | JWT — HS256, HttpOnly cookies, access + refresh token strategy |
| ML pipeline        | OpenAI (gpt-5.4-mini → gpt-5.4 two-pass classifier)            |
| News               | Finnhub (primary), yfinance (secondary)                        |
| Fundamentals       | yfinance                                                       |
| Push notifications | Telegram Bot API (webhook)                                     |
| Real-time          | WebSocket (`ConnectionManager` singleton)                      |
| Validation         | Pydantic v2                                                    |
| CI/CD              | GitHub Actions + Railway (backend + DB)                        |

---

## API surface
All routes are prefixed `/api/v1`. Interactive docs at `/docs` (Swagger) and `/redoc`.

---

## Data model

Core tables (all defined in `app/models/`):

- `users` — auth credentials, Telegram chat link
- `stocks` — US equity registry
- `theses` — per-user investment thesis, linked to a stock
- `quant_conditions` — metric / operator / threshold rows per thesis
- `catalysts` — qualitative event descriptions per thesis
- `evaluations` — per-sweep signal result (quant + catalyst JSON, bool signal)
- `alerts` — fired signals with delivery channel record
- `outcomes` — price at signal + 30-day outcome (ML calibration hook)
- `theses_proposals`, `catalyst_proposals`, `quant_proposals` — human-in-the-loop change queue

Migrations live in `db_migration/` (`V1.0__create_users_table.sql` → `V1.11__create_db_indexes.sql`).

---

## Local development

### Prerequisites

- Docker + Docker Compose
- Python 3.12

### 1. Clone and install

```bash
git clone https://github.com/brandontan2003/kestrel-backend.git
cd kestrel-backend
pip install -e ./common
pip install -r requirements.txt
```

### 2. Configure environment

Copy the template and fill in your values:

```bash
cp .env.example .env.dev
```

Required variables:

```bash
# Database (Docker Compose sets this automatically for local)
DATABASE_URL=postgresql+asyncpg://kestrel:password@localhost:5432/kestrel_dev

# Flyway (must use direct port 5432, not PgBouncer 6543)
FLYWAY_URL=jdbc:postgresql://localhost:5432/kestrel_dev
FLYWAY_USER=kestrel
FLYWAY_PASSWORD=password

# Frontend
FRONTEND_URL=http://localhost:5173

# Auth
JWT_SECRET_KEY=your-secret-here

# ML pipeline
FINNHUB_API_KEY=your-key
OPENAI_API_KEY=your-key

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_BOT_URL=https://your-tunnel-url/api/v1/telegram/webhook

# Scheduler (off by default — won't burn tokens unattended)
SCHEDULER_ENABLED=false
PROPOSALS_ENABLED=false
```

### 3. Start the database

```bash
docker-compose up kestrel-postgres kestrel-flyway
```

Flyway runs migrations automatically on startup and exits when done. The backend service in Compose depends on `service_completed_successfully` for Flyway, so order is guaranteed.

### 4. Run the backend

```bash
ENV=dev uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

### 5. Run everything via Docker Compose

```bash
docker-compose up          # postgres + flyway + backend
docker-compose down -v     # full reset (drops DB volume)
```

---

## Running tests

```bash
# All tests
python -m pytest

# Unit tests only (no DB required)
python -m pytest tests/unit/

# Integration tests (uses aiosqlite in-memory DB)
python -m pytest tests/integration/

# Specific file
python -m pytest tests/unit/test_theses_service.py -v

# Run ML Evaluation
OPENAI_API_KEY="your_api_key" python -m eval.run_eval --classify

```

---

## ML pipeline CLI

The `pipeline/` module has a standalone CLI for testing the news fetch + LLM classifier without starting the full server:

```bash
# Fetch and summarise recent NVDA news
python -m pipeline.run --ticker NVDA

# Multiple tickers, 3-day window, print each article
python -m pipeline.run --ticker NVDA AMD AAPL --days 3 --show

# Run the two-pass LLM classifier against ad-hoc catalysts
python -m pipeline.run --ticker NVDA --days 1 --limit 20 --classify \
    --catalyst "hyperscaler capex cut" \
    --catalyst "new export restrictions to China"
```

Output per ticker: article count, body-text rate (Pass 2 quote-rule viability), feed staleness, and per-source breakdown. With `--classify`: verdict, confidence, source kind, and supporting quote per article × catalyst pair.

---

## Key implementation decisions

**JWT auth** — Access tokens (15 min) + refresh tokens (7 days), both stored as `HttpOnly` cookies. WebSocket connections can't send cookies cross-origin, so the access token is passed as `?token=` query param instead.

**Layered architecture** — strict `router → service → repository` boundary. Repositories flush but never commit; `get_db` owns the transaction. Services have zero SQLAlchemy imports.

**Async SQLAlchemy** — `lazy="selectin"` on all relationships is a correctness requirement in async context, not a style choice.

**Flyway over Alembic** — handwritten SQL migrations give full control. Always run Flyway against the direct Postgres port (5432), not PgBouncer (6543) — advisory locks are incompatible with the connection pooler.

**Two-pass classifier** — gpt-5.4-mini drops ~90% of articles as irrelevant cheaply. gpt-5.4 only runs on what passes. No supporting quote = rejection. This is the anti-hallucination guard.

**Scheduler gates** — `SCHEDULER_ENABLED` and `PROPOSALS_ENABLED` are both `false` by default. An unattended sweep can't spend tokens or generate proposals without explicit opt-in.

**Telegram idempotency** — webhook handler always returns 200 (broad try/except), checks an idempotency guard before processing, and wraps sends in `_safe_send` so bot exceptions never propagate.

---

## Production deployment (Railway)
 
1. Push to `development` — GitHub Actions builds and deploys to Railway.
2. Flyway migrations run against Railway's **public** connection (`port 18386`).
3. The FastAPI app connects via Railway's **internal** connection (`port 5432`).
4. Set `DATABASE_URL` in Railway env to the internal string; keep a separate `FLYWAY_URL` pointing at the public port for migration runs.
5. `SCHEDULER_ENABLED=true` in production to activate the poll loop.

---

## Contributing

- Feature branches only — never push directly to `development`.
- Schema changes require a new `Vx.y__description.sql` migration file in `db_migration/`. Update `app/models/` to match.
- All PRs should include tests. New endpoints → integration test in `tests/integration/`. Service logic → unit test in `tests/unit/`.
- Keep `common/enums/` in sync with any new domain enum values — the frontend consumes this package.