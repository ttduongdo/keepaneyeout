from __future__ import annotations

import argparse
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.arxiv import fetch_arxiv
from app.db import SessionLocal
from app.models import Chunk, Document
from app.openai_client import embed_texts


def chunk_text(text: str, chunk_size: int = 400, overlap: int = 80) -> list[str]:
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    step = max(1, chunk_size - overlap)
    for start in range(0, len(words), step):
        chunk_words = words[start : start + chunk_size]
        if not chunk_words:
            break
        chunks.append(" ".join(chunk_words))
        if start + chunk_size >= len(words):
            break
    return chunks


def ingest_arxiv(query: str, max_results: int) -> tuple[int, int]:
    papers = fetch_arxiv(query=query, max_results=max_results)
    inserted_docs = 0
    inserted_chunks = 0

    with SessionLocal() as db:
        for paper in papers:
            if _exists(db, source="arxiv", external_id=paper.external_id):
                continue

            doc = Document(
                source="arxiv",
                external_id=paper.external_id,
                title=paper.title,
                url=paper.url,
                published_at=paper.published_at,
                metadata_json={"authors": paper.authors, "arxiv_id": paper.external_id},
            )
            db.add(doc)
            db.flush()

            text_chunks = chunk_text(paper.abstract)
            if not text_chunks:
                db.commit()
                inserted_docs += 1
                continue

            embeddings = embed_texts(text_chunks)
            for idx, (text_chunk, emb) in enumerate(zip(text_chunks, embeddings)):
                db.add(
                    Chunk(
                        document_id=doc.id,
                        chunk_index=idx,
                        text=text_chunk,
                        embedding=emb,
                    )
                )
                inserted_chunks += 1

            db.commit()
            inserted_docs += 1

    return inserted_docs, inserted_chunks


def _exists(db: Session, source: str, external_id: str) -> bool:
    stmt = select(Document.id).where(Document.source == source, Document.external_id == external_id)
    return db.execute(stmt).first() is not None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest arXiv abstracts into Postgres/pgvector")
    parser.add_argument("--query", required=True, help="arXiv query, e.g. cat:cs.LG OR cat:cs.AI")
    parser.add_argument("--max_results", type=int, default=25)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    docs, chunks = ingest_arxiv(query=args.query, max_results=args.max_results)
    print(f"Inserted {docs} documents and {chunks} chunks")


if __name__ == "__main__":
    main()
