from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, DocumentTopic, Topic, TopicRule

CONFIDENCE_THRESHOLD = 0.45
# TODO(topic centroid embeddings): replace rule-only confidence with centroid/classifier scoring.


@dataclass
class TopicMatch:
    topic_id: str
    confidence: float
    reason: str


def assign_topics_to_document(
    db: Session,
    document: Document,
    text: str,
    threshold: float = CONFIDENCE_THRESHOLD,
) -> list[DocumentTopic]:
    searchable_text = f"{document.title}\n{text}".lower()
    title_text = document.title.lower()
    categories = _extract_arxiv_categories(document)

    topic_rows = db.execute(select(TopicRule, Topic).join(Topic, TopicRule.topic_id == Topic.id)).all()
    existing_topic_ids = set(
        db.execute(select(DocumentTopic.topic_id).where(DocumentTopic.document_id == document.id)).scalars().all()
    )

    inserted: list[DocumentTopic] = []
    for rule, topic in topic_rows:
        include_keywords = [kw.lower() for kw in (rule.include_keywords or []) if kw]
        exclude_keywords = [kw.lower() for kw in (rule.exclude_keywords or []) if kw]
        category_rules = {cat.lower() for cat in (rule.arxiv_categories or []) if cat}

        include_hits = [kw for kw in include_keywords if kw in searchable_text]
        title_hits = [kw for kw in include_keywords if kw in title_text]
        exclude_hits = [kw for kw in exclude_keywords if kw in searchable_text]
        category_hits = sorted(categories.intersection(category_rules))

        if exclude_hits:
            continue
        if not include_hits and not category_hits:
            continue

        confidence = 0.0
        if include_hits:
            confidence += min(0.7, 0.25 + (0.12 * len(include_hits)))
        if title_hits:
            confidence += 0.1
        if category_hits:
            confidence += 0.25
        confidence = min(1.0, confidence)

        if confidence < threshold:
            continue
        if topic.id in existing_topic_ids:
            continue

        reasons: list[str] = []
        if include_hits:
            reasons.append("keywords=" + ", ".join(sorted(set(include_hits))[:6]))
        if category_hits:
            reasons.append("arxiv_categories=" + ", ".join(category_hits[:6]))
        reason = "; ".join(reasons) if reasons else "rule matched"

        link = DocumentTopic(document_id=document.id, topic_id=topic.id, confidence=confidence, reason=reason)
        db.add(link)
        inserted.append(link)

    return inserted


def _extract_arxiv_categories(document: Document) -> set[str]:
    metadata = document.metadata_json if isinstance(document.metadata_json, dict) else {}
    categories = metadata.get("categories", [])
    if not isinstance(categories, list):
        return set()
    return {str(category).strip().lower() for category in categories if str(category).strip()}
