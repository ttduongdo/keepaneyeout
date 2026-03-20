# AI Research Radar

AI Research Radar ingests AI research and discussions (arXiv + Hacker News), stores them in Postgres/pgvector, and serves a Pinterest‑style discovery feed with topic subscriptions, boards, and an interactive Trend Radar dashboard. It includes search, ask/RAG, builder modes, and newsletter digest pipelines.

## Architecture

```text
Ingestion (arXiv/HN) -> Topic Tagging -> Postgres/pgvector -> FastAPI -> Next.js
                                          |                    |
                                          v                    v
                               Trend Radar + Digests     Boards + Topics + Auth
```

## Quickstart

1. Start stack:

```bash
docker compose up --build
```

2. Migrate + seed topics:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed_topics.py
```

3. Ingest content:

```bash
docker compose exec backend python backend/scripts/ingestion/ingest_arxiv.py --max_results 100
docker compose exec backend python backend/scripts/ingestion/ingest_hackernews.py --max_items 100 --min_score 0 --related_k 3
docker compose exec backend python backend/scripts/ingestion/run_all.py
```

4. Generate digest:

```bash
docker compose exec backend python -m app.generate_digest --date 2026-02-23
```

5. Send newsletters (dry run):

```bash
docker compose exec backend python -m app.send_newsletters --date 2026-02-23 --dry_run true
```

## Reimplementation / Compare Modes

- `POST /reimplement`
- `POST /compare`

## Newsletter Endpoints

- `POST /subscriptions`
- `GET /digests?limit=30`
- `GET /digests/{date}`
- `GET /unsubscribe?token=...`

## Frontend Routes

- `/` discovery feed (boards + trending tab + topics)
- `/papers/search` search results
- `/builder` reimplement + compare
- `/digests` digest archive viewer
- `/subscribe` newsletter subscription form
- `/profile` topic subscriptions + boards

## Environment Variables

Frontend (Next.js):
- `NEXT_PUBLIC_API_BASE_URL` (required for production)

Backend (FastAPI):
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_EMBEDDING_MODEL`
- `OPENAI_CHAT_MODEL`
- `JWT_SECRET`
- `FRONTEND_URL` (CORS allowlist)
- `PUBLIC_APP_URL` (newsletter links)

Examples:
- `frontend/.env.local`
- `frontend/.env.production`
- `backend/.env.example`

## Deployment

Frontend (Vercel):
1. Import the `frontend` directory as a Vercel project.
2. Set `NEXT_PUBLIC_API_BASE_URL` to your backend URL (e.g., `https://your-backend.up.railway.app`).
3. Deploy.

Backend (Railway or Render):
1. Deploy the `backend` directory as a Python service.
2. Set environment variables (see `backend/.env.example`).
3. Set `FRONTEND_URL` to your Vercel domain (for CORS).
4. Run migrations: `alembic upgrade head`.

## Notes

- Topic subscriptions persist via backend `/user/topics`.
- Trending tab drives search when selecting a topic.
- Thumbnails are disabled in ingestion scripts (cards are text‑first).

## Future TODOs

- TODO(export as zip)
- TODO(project scaffolds)
- TODO(evaluation harness)
- TODO(topic centroid embeddings)
- TODO(topic-specific digests)
