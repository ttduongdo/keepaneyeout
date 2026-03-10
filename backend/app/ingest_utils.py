from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Chunk, Document
from app.openai_client import embed_texts
from app.topic_assignment import assign_topics_to_document


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


def document_exists(db: Session, source: str, external_id: str) -> bool:
    stmt = select(Document.id).where(Document.source == source, Document.external_id == external_id)
    return db.execute(stmt).first() is not None


def insert_document_with_chunks(db: Session, doc: Document, text_to_embed: str) -> int:
    db.add(doc)
    db.flush()

    text_chunks = chunk_text(text_to_embed)
    if not text_chunks:
        db.commit()
        return 0

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

    assign_topics_to_document(db=db, document=doc, text=text_to_embed)
    db.commit()
    return len(text_chunks)
