from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from app.models import Chunk, Document, DocumentTopic, Topic, User, UserTopic
from app.services.openai_client import chat_markdown
from app.routes.schemas import PaperDetailResponse, PaperFeedItem, PaperFeedResponse, TrendSummaryResponse


def get_user_topics(db: Session, user: User) -> list[str]:
    return db.execute(select(UserTopic.topic).where(UserTopic.user_id == user.id)).scalars().all()


def fetch_feed(
    db: Session,
    section: str,
    page: int,
    page_size: int,
    topics: list[str] | None,
) -> PaperFeedResponse:
    offset = (page - 1) * page_size
    query = select(Document)

    if topics:
        query = (
            query.join(DocumentTopic, DocumentTopic.document_id == Document.id)
            .join(Topic, Topic.id == DocumentTopic.topic_id)
            .where(Topic.name.in_(topics))
        )

    if section == "trending":
        query = query.order_by(desc(Document.published_at))
    elif section == "recommended":
        query = query.order_by(desc(Document.published_at))
    else:
        query = query.order_by(desc(Document.published_at))

    total_items = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    if topics and total_items == 0:
        query = select(Document)
        total_items = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    docs = db.execute(query.offset(offset).limit(page_size)).scalars().all()

    items = [_document_to_feed_item(db, doc) for doc in docs]
    has_more = offset + page_size < total_items

    return PaperFeedResponse(items=items, page=page, has_more=has_more)


def _document_to_feed_item(db: Session, doc: Document) -> PaperFeedItem:
    summary = doc.summary or _get_summary(db, doc)
    tags = get_document_tags(db, doc)
    authors = doc.authors or []

    return PaperFeedItem(
        id=doc.id,
        title=doc.title,
        authors=authors,
        summary=summary,
        tags=tags,
        published_date=doc.published_at,
        url=doc.url,
    )


def _get_summary(db: Session, doc: Document) -> str:
    if doc.summary:
        return doc.summary
    chunk = db.execute(
        select(Chunk).where(Chunk.document_id == doc.id).order_by(Chunk.chunk_index.asc()).limit(1)
    ).scalar_one_or_none()
    if not chunk:
        return ""
    return chunk.text[:400]


def get_document_tags(db: Session, doc: Document) -> list[str]:
    rows = db.execute(
        select(Topic.name)
        .join(DocumentTopic, DocumentTopic.topic_id == Topic.id)
        .where(DocumentTopic.document_id == doc.id)
        .order_by(DocumentTopic.confidence.desc())
    ).scalars().all()
    if rows:
        return list(rows)
    metadata = doc.metadata_json if isinstance(doc.metadata_json, dict) else {}
    categories = metadata.get("categories", [])
    return [str(cat) for cat in categories if cat]


def generate_trend_summary(db: Session) -> TrendSummaryResponse:
    now = datetime.now(tz=UTC)
    window_start = now - timedelta(days=7)

    docs = db.execute(
        select(Document).where(
            and_(Document.published_at >= window_start, Document.source.in_(["arxiv", "hackernews"]))
        ).order_by(Document.published_at.desc()).limit(30)
    ).scalars().all()

    if not docs:
        return TrendSummaryResponse(summary_md="No recent papers to summarize.")

    topic_counts: dict[str, int] = {}
    for doc in docs:
        for tag in get_document_tags(db, doc)[:3]:
            topic_counts[tag] = topic_counts.get(tag, 0) + 1

    top_topics = sorted(topic_counts.items(), key=lambda kv: kv[1], reverse=True)[:6]
    topic_lines = "\n".join([f"- {name} ({count})" for name, count in top_topics])

    system_prompt = (
        "You summarize weekly AI research trends. Use 3-5 bullet points grounded in the given context."
    )
    user_prompt = (
        "Recent topics:\n"
        f"{topic_lines}\n\n"
        "Recent papers/discussions:\n"
        + "\n".join([f"- {doc.title}" for doc in docs[:12]])
    )

    summary_md = chat_markdown(system_prompt=system_prompt, user_prompt=user_prompt)
    return TrendSummaryResponse(summary_md=summary_md)


def get_paper_detail(db: Session, paper_id: str) -> PaperDetailResponse | None:
    try:
        paper_uuid = UUID(paper_id)
    except ValueError:
        return None
    doc = db.execute(select(Document).where(Document.id == paper_uuid)).scalar_one_or_none()
    if doc is None:
        return None
    summary = _get_summary(db, doc)
    tags = get_document_tags(db, doc)
    metadata = doc.metadata_json if isinstance(doc.metadata_json, dict) else {}
    authors = metadata.get("authors", "") or metadata.get("author", "") or metadata.get("by", "")
    abstract = metadata.get("abstract", "") or summary
    summary_full = metadata.get("summary", "") or summary
    return PaperDetailResponse(
        id=doc.id,
        title=doc.title,
        authors=authors,
        summary=summary,
        summary_full=summary_full,
        abstract=abstract,
        tags=tags,
        published_date=doc.published_at,
        url=doc.url,
    )


def get_related_papers(db: Session, paper_id: str, limit: int = 6) -> list[PaperFeedItem]:
    try:
        paper_uuid = UUID(paper_id)
    except ValueError:
        return []

    seed_chunk = db.execute(
        select(Chunk).where(Chunk.document_id == paper_uuid).order_by(Chunk.chunk_index.asc()).limit(1)
    ).scalar_one_or_none()
    if seed_chunk is None:
        return []

    distance = Chunk.embedding.cosine_distance(seed_chunk.embedding)
    rows = db.execute(
        select(Chunk, Document)
        .join(Document, Chunk.document_id == Document.id)
        .where(Chunk.document_id != paper_uuid)
        .order_by(distance)
        .limit(limit * 4)
    ).all()

    seen: set[str] = set()
    related: list[PaperFeedItem] = []
    for chunk, doc in rows:
        if str(doc.id) in seen:
            continue
        seen.add(str(doc.id))
        related.append(_document_to_feed_item(db, doc))
        if len(related) >= limit:
            break
    return related
