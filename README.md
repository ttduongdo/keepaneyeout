# AI Research Radar

AI Research Radar is a minimal full-stack RAG research tracker that ingests arXiv papers, stores chunk embeddings in Postgres + pgvector, and provides semantic search + citation-backed Q&A via FastAPI and a lightweight Next.js UI.

## Architecture (Baseline)

```text
arXiv API
   |
   v
Ingestion CLI (Python)
   |
   v
OpenAI Embeddings -----> Postgres + pgvector
                               |
                               v
                         FastAPI (/search, /ask)
                               |
                               v
                        Next.js + Tailwind UI
```

## Repo Structure

```text
.
├── docker-compose.yml
├── README.md
├── backend
│   ├── Dockerfile
│   ├── README.md
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/0001_initial.py
│   ├── app
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── db.py
│   │   ├── config.py
│   │   ├── schemas.py
│   │   ├── rag.py
│   │   ├── openai_client.py
│   │   ├── arxiv.py
│   │   └── ingest_arxiv.py
│   └── tests/test_api.py
└── frontend
    ├── Dockerfile
    ├── README.md
    ├── package.json
    ├── next.config.js
    ├── tailwind.config.ts
    └── app
        ├── layout.tsx
        ├── page.tsx
        └── globals.css
```

## Quickstart

1. Set environment variables in your shell:

```bash
export OPENAI_API_KEY=your_key_here
export OPENAI_EMBEDDING_MODEL=text-embedding-3-large
export OPENAI_CHAT_MODEL=gpt-4o-mini
```

2. Start everything:

```bash
docker compose up --build
```

3. Ingest arXiv data (new terminal):

```bash
docker compose exec backend python -m app.ingest_arxiv --query "cat:cs.LG OR cat:cs.AI" --max_results 25
```

4. Open UI: http://localhost:3000

## Database Schema

- `documents`
  - `id` (uuid, pk)
  - `source` (text)
  - `external_id` (text)
  - `title` (text)
  - `url` (text)
  - `published_at` (timestamptz)
  - `metadata` (jsonb)
  - `created_at` (timestamptz)
  - unique: (`source`, `external_id`)
- `chunks`
  - `id` (uuid, pk)
  - `document_id` (uuid, fk -> documents.id)
  - `chunk_index` (int)
  - `text` (text)
  - `embedding` (vector)
  - `created_at` (timestamptz)

## API Endpoints

- `GET /health`
- `GET /search?q=...&k=10`
- `POST /ask` with body: `{ "query": "...", "k": 8 }`

### Manual curl: `/search`

```bash
curl "http://localhost:8000/search?q=long-context%20transformers&k=5"
```

### Manual curl: `/ask`

```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"query":"What are recent trends in efficient LLM training?", "k":8}'
```

Expected: response includes `answer` and `citations` (typically >=2 once data is ingested).

## TODO (Intentionally Not in Baseline)

- TODO: Reddit/Medium ingestion
- TODO: reranking
- TODO: digest
- TODO: trending clusters
