from __future__ import annotations

import argparse
import math
from pathlib import Path
import re
import sys
from typing import Iterable

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))

from scripts.ingestion._env import load_project_env  # noqa: E402

load_project_env()

from datetime import UTC, datetime  # noqa: E402

from app.services.arxiv import fetch_arxiv  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.services.ingest_utils import document_exists, insert_document_with_chunks  # noqa: E402
from app.models import Chunk, Document  # noqa: E402
from app.services.openai_client import embed_texts  # noqa: E402

STOPWORDS = {"the", "and", "for", "with", "from", "using", "into", "via", "toward", "towards"}


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _title_query(title: str, max_terms: int = 6) -> str:
    tokens = [t.lower() for t in re.findall(r"[A-Za-z0-9\-]+", title) if len(t) > 3]
    tokens = [t for t in tokens if t not in STOPWORDS]
    phrase = " ".join(tokens[:max_terms])
    if not phrase:
        return "all:machine learning"
    return f'all:"{phrase}"'


def _fetch_seed_embeddings(db, seed_arxiv_ids: Iterable[str]) -> list[tuple[str, list[float]]]:
    rows = (
        db.query(Document)
        .filter(Document.source == "arxiv", Document.external_id.in_(list(seed_arxiv_ids)))
        .all()
    )
    result: list[tuple[str, list[float]]] = []
    for doc in rows:
        chunk = (
            db.query(Chunk)
            .filter(Chunk.document_id == doc.id)
            .order_by(Chunk.chunk_index.asc())
            .first()
        )
        if chunk:
            result.append((doc.external_id, chunk.embedding))
    return result


def expand_similar_papers(
    seed_arxiv_ids: list[str] | None = None,
    max_candidates: int = 6,
    similarity_threshold: float = 0.78,
) -> int:
    inserted = 0

    with SessionLocal() as db:
        if seed_arxiv_ids is None:
            recent = (
                db.query(Document)
                .filter(Document.source == "arxiv")
                .order_by(Document.created_at.desc())
                .limit(25)
                .all()
            )
            seed_arxiv_ids = [doc.external_id for doc in recent]

        seed_embeddings = _fetch_seed_embeddings(db, seed_arxiv_ids)

        for external_id, seed_embedding in seed_embeddings:
            seed_doc = db.query(Document).filter(Document.source == "arxiv", Document.external_id == external_id).first()
            if not seed_doc:
                continue

            query = _title_query(seed_doc.title)
            candidates = fetch_arxiv(query=query, max_results=max_candidates)
            for paper in candidates:
                if document_exists(db, source="arxiv", external_id=paper.external_id):
                    continue

                text_to_embed = f"Title: {paper.title}\n\nAbstract: {paper.abstract}"
                try:
                    candidate_embedding = embed_texts([text_to_embed])[0]
                except Exception as exc:
                    print(f"[error] failed embedding expansion candidate {paper.external_id}: {exc}")
                    continue

                similarity = cosine_similarity(seed_embedding, candidate_embedding)
                if similarity < similarity_threshold:
                    continue

                try:
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
                            "seed_arxiv_id": external_id,
                            "similarity": similarity,
                        },
                    )
                    doc.embedding = embed_texts([text_to_embed])[0]
                    insert_document_with_chunks(db=db, doc=doc, text_to_embed=text_to_embed)
                    inserted += 1
                except Exception as exc:
                    db.rollback()
                    print(f"[error] failed expansion insert {paper.external_id}: {exc}")

    return inserted


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Expand arXiv coverage using similarity search")
    parser.add_argument("--max_candidates", type=int, default=6)
    parser.add_argument("--similarity_threshold", type=float, default=0.78)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    inserted = expand_similar_papers(
        seed_arxiv_ids=None,
        max_candidates=args.max_candidates,
        similarity_threshold=args.similarity_threshold,
    )
    print(f"Similarity expansion summary: inserted_docs={inserted}")


if __name__ == "__main__":
    main()
