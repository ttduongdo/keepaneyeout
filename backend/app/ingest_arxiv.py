from __future__ import annotations

import argparse

from app.arxiv import fetch_arxiv
from app.db import SessionLocal
from app.ingest_utils import document_exists, insert_document_with_chunks
from app.models import Document


def ingest_arxiv(query: str, max_results: int) -> tuple[int, int, int, int]:
    papers = fetch_arxiv(query=query, max_results=max_results)
    inserted_docs = 0
    inserted_chunks = 0
    skipped_duplicates = 0
    errors = 0

    with SessionLocal() as db:
        for paper in papers:
            try:
                if document_exists(db, source="arxiv", external_id=paper.external_id):
                    skipped_duplicates += 1
                    continue

                doc = Document(
                    source="arxiv",
                    external_id=paper.external_id,
                    title=paper.title,
                    url=paper.url,
                    published_at=paper.published_at,
                    metadata_json={
                        "authors": paper.authors,
                        "categories": paper.categories,
                        "arxiv_id": paper.external_id,
                    },
                )
                text_to_embed = f"Title: {paper.title}\n\nAbstract: {paper.abstract}"
                chunks_added = insert_document_with_chunks(db=db, doc=doc, text_to_embed=text_to_embed)
                inserted_docs += 1
                inserted_chunks += chunks_added
            except Exception as exc:
                db.rollback()
                errors += 1
                print(f"[error] failed processing arXiv paper {paper.external_id}: {exc}")

    return inserted_docs, inserted_chunks, skipped_duplicates, errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest arXiv abstracts into Postgres/pgvector")
    parser.add_argument("--query", required=True, help="arXiv query, e.g. cat:cs.LG OR cat:cs.AI")
    parser.add_argument("--max_results", type=int, default=50)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    docs, chunks, skipped, errors = ingest_arxiv(query=args.query, max_results=args.max_results)
    print(
        "Ingestion summary: "
        f"inserted_docs={docs}, inserted_chunks={chunks}, skipped_duplicates={skipped}, errors={errors}"
    )


if __name__ == "__main__":
    main()
