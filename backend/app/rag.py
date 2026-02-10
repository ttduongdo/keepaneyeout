from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import Chunk, Document
from app.openai_client import chat_with_context, embed_texts
from app.schemas import AskResponse, Citation, SearchResult


def _base_search_stmt(query_embedding: list[float], k: int) -> Select:
    distance = Chunk.embedding.cosine_distance(query_embedding)
    score = (1 - distance).label("score")

    return (
        select(Chunk, Document, score)
        .join(Document, Chunk.document_id == Document.id)
        .order_by(distance)
        .limit(k)
    )


def semantic_search(db: Session, query: str, k: int = 10) -> list[SearchResult]:
    query_embedding = embed_texts([query])[0]
    rows = db.execute(_base_search_stmt(query_embedding, k)).all()

    return [
        SearchResult(
            chunk_id=chunk.id,
            document_id=doc.id,
            title=doc.title,
            url=doc.url,
            source=doc.source,
            published_at=doc.published_at,
            snippet=chunk.text[:350],
            score=float(score),
        )
        for chunk, doc, score in rows
    ]


def ask_question(db: Session, query: str, k: int = 8) -> AskResponse:
    query_embedding = embed_texts([query])[0]
    rows = db.execute(_base_search_stmt(query_embedding, k)).all()

    context_blocks = []
    citations: list[Citation] = []
    for idx, (chunk, doc, _score) in enumerate(rows, start=1):
        snippet = chunk.text[:350]
        context_blocks.append(
            f"[{idx}] {doc.title}\nURL: {doc.url}\nSnippet: {snippet}"
        )
        citations.append(
            Citation(
                document_id=doc.id,
                title=doc.title,
                url=doc.url,
                chunk_id=chunk.id,
                snippet=snippet,
            )
        )

    answer = chat_with_context(query=query, context_blocks=context_blocks)
    return AskResponse(answer=answer, citations=citations)
