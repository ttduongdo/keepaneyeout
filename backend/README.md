# Backend (FastAPI)

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
```

## Required Environment Variables

- `DATABASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_EMBEDDING_MODEL`
- `OPENAI_CHAT_MODEL`
- `EMAIL_PROVIDER` (`resend`)
- `RESEND_API_KEY`
- `FROM_EMAIL`
- `PUBLIC_APP_URL`

## Run API

```bash
cd backend
alembic upgrade head
python -m app.seed_topics
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Ingestion

```bash
python -m app.ingest_arxiv --query "cat:cs.LG OR cat:cs.AI" --max_results 50
python -m app.ingest_hackernews --list topstories --max_items 50 --min_score 0 --include_comments false --max_comments 0
```

## Digest Generation

```bash
python -m app.generate_digest --date 2026-02-23
```

## Newsletter Sending

Dry run (writes HTML files to `newsletter_dry_run/<date>/`):

```bash
python -m app.send_newsletters --date 2026-02-23 --dry_run true
```

Real send:

```bash
python -m app.send_newsletters --date 2026-02-23 --dry_run false
```

## Newsletter APIs

Create/upsert subscription:

```bash
curl -X POST "http://localhost:8000/subscriptions" \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","topic_ids":[],"frequency":"daily"}'
```

List digests:

```bash
curl "http://localhost:8000/digests?limit=30"
```

Get digest by date:

```bash
curl "http://localhost:8000/digests/2026-02-23"
```

Unsubscribe:

```bash
curl "http://localhost:8000/unsubscribe?token=<token>"
```

## Tests

```bash
cd backend
pytest -q
```
