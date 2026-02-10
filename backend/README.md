# Backend (FastAPI)

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
```

## Environment Variables

- `DATABASE_URL`
  - Host run (recommended for backend README flow): `postgresql+psycopg://postgres:postgres@localhost:5433/research_radar`
  - Docker-internal hostname (`postgres`) is only for containers on the compose network.
- `OPENAI_API_KEY`
- `OPENAI_EMBEDDING_MODEL` (default: `text-embedding-3-large`)
  - Current schema uses `vector(3072)`, so use a 3072-dim embedding model unless you regenerate migrations/schema.
  - Baseline uses exact vector search (no ANN index) for compatibility.
- `OPENAI_CHAT_MODEL` (default: `gpt-4o-mini`)
- `CORS_ALLOW_ORIGINS` (default: `*`)

## Run API

1. Ensure Postgres is running on `localhost:5433` (for example: `docker compose up -d postgres` from repo root).
2. Run migrations and API:

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Ingest arXiv

```bash
cd backend
python -m app.ingest_arxiv --query "cat:cs.LG OR cat:cs.AI" --max_results 25
```

## Tests

```bash
cd backend
pytest
```
