from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))

from backend.scripts.ingestion._env import load_project_env  # noqa: E402

load_project_env()

from app.db import SessionLocal  # noqa: E402
from app.services.hackernews import fetch_item as _fetch_item, fetch_story_ids as _fetch_story_ids, strip_html as _strip_html, clean_text as _clean_text  # noqa: E402
from app.services.ingest_utils import document_exists, insert_document_with_chunks  # noqa: E402
from app.models import Chunk, Document  # noqa: E402
from app.services.openai_client import embed_texts  # noqa: E402

KEYWORDS = ["ai", "machine learning", "transformer", "llm"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest Hacker News AI discussions")
    parser.add_argument("--max_items", type=int, default=100)
    parser.add_argument("--min_score", type=int, default=0)
    parser.add_argument("--related_k", type=int, default=3)
    return parser.parse_args()


def _matches_keywords(title: str) -> bool:
    lowered = title.lower()
    return any(keyword in lowered for keyword in KEYWORDS)


def _attach_related_papers(db, doc: Document, related_k: int) -> None:
    seed_chunk = (
        db.query(Chunk)
        .filter(Chunk.document_id == doc.id)
        .order_by(Chunk.chunk_index.asc())
        .first()
    )
    if seed_chunk is None:
        return

    distance = Chunk.embedding.cosine_distance(seed_chunk.embedding)
    rows = (
        db.query(Chunk, Document)
        .join(Document, Chunk.document_id == Document.id)
        .filter(Document.source == "arxiv")
        .order_by(distance)
        .limit(related_k * 3)
        .all()
    )

    related_ids: list[str] = []
    seen = set()
    for _chunk, paper in rows:
        if paper.id in seen:
            continue
        seen.add(paper.id)
        related_ids.append(str(paper.id))
        if len(related_ids) >= related_k:
            break

    metadata = doc.metadata_json if isinstance(doc.metadata_json, dict) else {}
    metadata["related_paper_ids"] = related_ids
    doc.metadata_json = metadata
    db.commit()


def ingest_hackernews(max_items: int, min_score: int, related_k: int) -> tuple[int, int, int, int]:
    inserted_docs = 0
    inserted_chunks = 0
    skipped = 0
    errors = 0

    with SessionLocal() as db:
        try:
            story_ids = _fetch_story_ids("topstories")[:max_items]
        except Exception as exc:
            print(f"[error] failed to fetch HN list: {exc}")
            return 0, 0, 0, 1

        for story_id in story_ids:
            try:
                item = _fetch_item(story_id)
            except Exception as exc:
                errors += 1
                print(f"[error] failed fetching item {story_id}: {exc}")
                continue

            if not item or item.get("type") != "story":
                skipped += 1
                continue
            if item.get("deleted") or item.get("dead"):
                skipped += 1
                continue

            title = _clean_text(item.get("title"))
            if not title or not _matches_keywords(title):
                skipped += 1
                continue
            if int(item.get("score") or 0) < min_score:
                skipped += 1
                continue

            external_id = str(item.get("id"))
            if document_exists(db, source="hackernews", external_id=external_id):
                skipped += 1
                continue

            try:
                story_url = item.get("url") or f"https://news.ycombinator.com/item?id={external_id}"
                published_at = datetime.fromtimestamp(int(item.get("time", 0) or 0), tz=UTC)

                body = _strip_html(item.get("text", ""))
                text_to_embed = f"Title: {title}\n\nBody: {body}" if body else f"Title: {title}"

                summary = (body or title)[:600]
                doc = Document(
                    source="hackernews",
                    external_id=external_id,
                    title=title,
                    url=story_url,
                    summary=summary,
                    authors=[item.get("by")] if item.get("by") else [],
                    published_at=published_at,
                    ingested_at=datetime.now(tz=UTC),
                    metadata_json={
                        "by": item.get("by"),
                        "score": item.get("score"),
                        "descendants": item.get("descendants"),
                        "type": item.get("type"),
                        "list_name": "topstories",
                    },
                )

                doc.embedding = embed_texts([text_to_embed])[0]
                chunks_added = insert_document_with_chunks(db=db, doc=doc, text_to_embed=text_to_embed)
                inserted_docs += 1
                inserted_chunks += chunks_added

                _attach_related_papers(db, doc, related_k=related_k)
            except Exception as exc:
                db.rollback()
                errors += 1
                print(f"[error] failed processing item {story_id}: {exc}")

    return inserted_docs, inserted_chunks, skipped, errors


def main() -> None:
    args = parse_args()
    docs, chunks, skipped, errors = ingest_hackernews(
        max_items=args.max_items,
        min_score=args.min_score,
        related_k=args.related_k,
    )
    print(
        "Ingestion summary: "
        f"inserted_docs={docs}, inserted_chunks={chunks}, skipped={skipped}, errors={errors}"
    )


if __name__ == "__main__":
    main()
