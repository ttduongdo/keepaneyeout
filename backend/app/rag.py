from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import Chunk, Document, DocumentTopic, Topic
from app.openai_client import chat_with_context, embed_texts
from app.schemas import AskResponse, Citation, SearchResponse, SearchResult, TopicRef


def _base_search_stmt(query_embedding: list[float], k: int, topic_id: UUID | None = None) -> Select:
    distance = Chunk.embedding.cosine_distance(query_embedding)
    score = (1 - distance).label("score")

    stmt = select(Chunk, Document, score).join(Document, Chunk.document_id == Document.id)
    if topic_id is not None:
        stmt = stmt.join(DocumentTopic, DocumentTopic.document_id == Document.id).where(DocumentTopic.topic_id == topic_id)

    return stmt.order_by(distance).limit(k)


def _resolve_topic(db: Session, topic: str | None) -> Topic | None:
    if topic is None or not topic.strip():
        return None

    topic = topic.strip()
    topic_uuid: UUID | None = None
    try:
        topic_uuid = UUID(topic)
    except ValueError:
        topic_uuid = None

    if topic_uuid is not None:
        found = db.execute(select(Topic).where(Topic.id == topic_uuid)).scalar_one_or_none()
    else:
        found = db.execute(select(Topic).where(Topic.name.ilike(topic))).scalar_one_or_none()

    if found is None:
        raise ValueError(f"Unknown topic: {topic}")
    return found


def _retrieve_rows(
    db: Session,
    query_embedding: list[float],
    k: int,
    topic: str | None = None,
) -> tuple[list[tuple[Chunk, Document, float, bool]], TopicRef | None]:
    active_topic = _resolve_topic(db, topic)

    if active_topic is None:
        rows = db.execute(_base_search_stmt(query_embedding=query_embedding, k=k)).all()
        merged = [(chunk, doc, float(score), False) for chunk, doc, score in rows]
        return merged, None

    filtered_rows = db.execute(_base_search_stmt(query_embedding=query_embedding, k=k, topic_id=active_topic.id)).all()
    merged: list[tuple[Chunk, Document, float, bool]] = [
        (chunk, doc, float(score), True) for chunk, doc, score in filtered_rows
    ]

    if len(merged) < k:
        existing_chunk_ids = {chunk.id for chunk, _doc, _score, _topic_match in merged}
        global_rows = db.execute(_base_search_stmt(query_embedding=query_embedding, k=k * 3)).all()
        for chunk, doc, score in global_rows:
            if chunk.id in existing_chunk_ids:
                continue
            merged.append((chunk, doc, float(score), False))
            if len(merged) >= k:
                break

    topic_ref = TopicRef(id=active_topic.id, name=active_topic.name)
    return merged[:k], topic_ref


def semantic_search(db: Session, query: str, k: int = 10, topic: str | None = None) -> SearchResponse:
    query_embedding = embed_texts([query])[0]
    rows, active_topic = _retrieve_rows(db=db, query_embedding=query_embedding, k=k, topic=topic)

    results = [
        SearchResult(
            chunk_id=chunk.id,
            document_id=doc.id,
            title=doc.title,
            url=doc.url,
            source=doc.source,
            published_at=doc.published_at,
            snippet=chunk.text[:350],
            score=score,
            topic_match=topic_match,
        )
        for chunk, doc, score, topic_match in rows
    ]

    return SearchResponse(active_topic=active_topic, results=results)


def ask_question(db: Session, query: str, k: int = 8, topic: str | None = None) -> AskResponse:
    query_embedding = embed_texts([query])[0]
    rows, active_topic = _retrieve_rows(db=db, query_embedding=query_embedding, k=k, topic=topic)

    if not rows:
        return AskResponse(active_topic=active_topic, answer="No relevant context found.", citations=[])

    context_blocks = []
    citations: list[Citation] = []
    for idx, (chunk, doc, _score, topic_match) in enumerate(rows, start=1):
        snippet = chunk.text[:350]
        context_blocks.append(
            f"[{idx}] {doc.title}\nURL: {doc.url}\nSnippet: {snippet}\nTopicMatch: {topic_match}"
        )
        citations.append(
            Citation(
                document_id=doc.id,
                title=doc.title,
                url=doc.url,
                chunk_id=chunk.id,
                snippet=snippet,
                topic_match=topic_match,
            )
        )

    answer = chat_with_context(query=query, context_blocks=context_blocks)
    return AskResponse(active_topic=active_topic, answer=answer, citations=citations)
