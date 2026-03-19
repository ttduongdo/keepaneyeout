from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))

from backend.scripts.ingestion.ingest_arxiv import ingest_arxiv  # noqa: E402
from backend.scripts.ingestion.ingest_hackernews import ingest_hackernews  # noqa: E402
from app.services.trend_service import update_trends  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from backend.scripts.ingestion._env import load_project_env  # noqa: E402

load_project_env()


def main() -> None:
    ingest_arxiv(max_results=100, expand_similar=True, similarity_threshold=0.78)
    ingest_hackernews(max_items=100, min_score=0, related_k=3)
    with SessionLocal() as db:
        update_trends(db)


if __name__ == "__main__":
    main()
