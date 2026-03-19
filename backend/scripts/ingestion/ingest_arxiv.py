from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Iterable

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))

from backend.scripts.ingestion._env import load_project_env  # noqa: E402

load_project_env()

from datetime import UTC, datetime  # noqa: E402

from app.services.arxiv import fetch_arxiv  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.services.ingest_utils import document_exists, insert_document_with_chunks  # noqa: E402
from app.models import Document  # noqa: E402
from app.services.openai_client import embed_texts  # noqa: E402
from backend.scripts.ingestion.expand_similar_papers import expand_similar_papers  # noqa: E402

CATEGORIES = ["cs.AI", "cs.LG", "cs.CL", "cs.CV", "stat.ML"]


def build_query(categories: Iterable[str]) -> str:
    return " OR ".join([f"cat:{category}" for category in categories])


def ingest_arxiv(max_results: int, expand_similar: bool, similarity_threshold: float) -> tuple[int, int, int, int]:
    query = build_query(CATEGORIES)
    papers = fetch_arxiv(query=query, max_results=max_results)

    inserted_docs = 0
    inserted_chunks = 0
    skipped_duplicates = 0
    errors = 0
    new_ids: list[str] = []

    with SessionLocal() as db:
        for paper in papers:
            try:
                if document_exists(db, source="arxiv", external_id=paper.external_id):
                    skipped_duplicates += 1
                    continue

                summary = paper.abstract[:600]
                doc = Document(
                    source="arxiv",
                    external_id=paper.external_id,
                    title=paper.title,
                    url=paper.url,
                    summary=summary,
                    authors=paper.authors,
                    published_at=paper.published_at,
                    ingested_at=datetime.now(tz=UTC),
                    metadata_json={
                        "authors": paper.authors,
                        "categories": paper.categories,
                        "arxiv_id": paper.external_id,
                        "abstract": paper.abstract,
                        "summary": summary,
                    },
                )

                text_to_embed = f"Title: {paper.title}\n\nAbstract: {paper.abstract}"
                doc.embedding = embed_texts([text_to_embed])[0]
                chunks_added = insert_document_with_chunks(db=db, doc=doc, text_to_embed=text_to_embed)
                inserted_docs += 1
                inserted_chunks += chunks_added
                new_ids.append(paper.external_id)
            except Exception as exc:
                db.rollback()
                errors += 1
                print(f"[error] failed processing arXiv paper {paper.external_id}: {exc}")

    if expand_similar and new_ids:
        expanded = expand_similar_papers(
            seed_arxiv_ids=new_ids,
            max_candidates=6,
            similarity_threshold=similarity_threshold,
        )
        print(f"Similarity expansion: inserted_docs={expanded}")

    return inserted_docs, inserted_chunks, skipped_duplicates, errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest newest arXiv papers into Postgres/pgvector")
    parser.add_argument("--max_results", type=int, default=100)
    parser.add_argument("--expand_similar", type=_parse_bool, default=True)
    parser.add_argument("--similarity_threshold", type=float, default=0.78)
    return parser.parse_args()


def _parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError("Expected boolean value")


def main() -> None:
    args = parse_args()
    docs, chunks, skipped, errors = ingest_arxiv(
        max_results=args.max_results,
        expand_similar=args.expand_similar,
        similarity_threshold=args.similarity_threshold,
    )
    print(
        "Ingestion summary: "
        f"inserted_docs={docs}, inserted_chunks={chunks}, skipped_duplicates={skipped}, errors={errors}"
    )


if __name__ == "__main__":
    main()
