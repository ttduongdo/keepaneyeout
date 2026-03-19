from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import UUID

import markdown
from sqlalchemy import Select, and_, select
from sqlalchemy.orm import Session

from app.services.config import settings
from app.services.email_provider import EmailMessage, EmailProvider, build_email_provider
from app.models import Digest, Document, DocumentTopic, Subscription, Topic


@dataclass
class NewsletterResult:
    date: date
    recipients_considered: int
    recipients_sent: int
    dry_run: bool
    output_dir: str | None


def generate_digest_for_date(db: Session, digest_date: date, frequency: str = "daily") -> Digest:
    if frequency not in {"daily", "weekly"}:
        raise ValueError("frequency must be one of daily|weekly")

    end_dt = datetime.combine(digest_date + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    start_dt = end_dt - (timedelta(days=7) if frequency == "weekly" else timedelta(days=1))

    docs = _fetch_documents(db=db, start_dt=start_dt, end_dt=end_dt)
    topic_map = _fetch_document_topic_map(db=db, document_ids=[doc.id for doc in docs]) if docs else {}

    top_papers = [doc for doc in docs if doc.source == "arxiv"][:8]
    top_discussions = sorted(
        [doc for doc in docs if doc.source == "hackernews"],
        key=lambda doc: _hn_velocity_score(doc=doc, window_end=end_dt),
        reverse=True,
    )[:8]

    topic_counts: dict[str, int] = {}
    for doc in docs:
        topic_name = topic_map.get(doc.id)
        key = topic_name or f"source:{doc.source}"
        topic_counts[key] = topic_counts.get(key, 0) + 1

    stats = {
        "total_documents": len(docs),
        "source_counts": _source_counts(docs),
        "topic_counts": topic_counts,
        "window_start": start_dt.isoformat(),
        "window_end": end_dt.isoformat(),
    }

    content_md = _render_digest_markdown(
        digest_date=digest_date,
        top_papers=top_papers,
        top_discussions=top_discussions,
        topic_counts=topic_counts,
        stats=stats,
    )

    return _upsert_digest(db=db, digest_date=digest_date, content_md=content_md, stats=stats)


def list_digests(db: Session, limit: int = 30) -> list[Digest]:
    stmt: Select = select(Digest).order_by(Digest.date.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_digest_by_date(db: Session, digest_date: date) -> Digest | None:
    return db.execute(select(Digest).where(Digest.date == digest_date)).scalar_one_or_none()


def upsert_subscription(
    db: Session,
    email: str,
    topic_ids: list[UUID] | None,
    frequency: str,
) -> Subscription:
    normalized_email = email.strip().lower()
    if not normalized_email:
        raise ValueError("email is required")
    if frequency not in {"daily", "weekly"}:
        raise ValueError("frequency must be one of daily|weekly")

    subscription = db.execute(select(Subscription).where(Subscription.email == normalized_email)).scalar_one_or_none()
    if subscription is None:
        subscription = Subscription(
            email=normalized_email,
            topic_ids=topic_ids or [],
            frequency=frequency,
            is_active=True,
            unsubscribe_token=secrets.token_urlsafe(24),
        )
        db.add(subscription)
    else:
        subscription.topic_ids = topic_ids or []
        subscription.frequency = frequency
        subscription.is_active = True

    db.commit()
    db.refresh(subscription)
    return subscription


def unsubscribe_subscription(db: Session, token: str) -> bool:
    subscription = db.execute(select(Subscription).where(Subscription.unsubscribe_token == token)).scalar_one_or_none()
    if subscription is None:
        return False

    subscription.is_active = False
    db.commit()
    return True


def send_newsletters_for_date(
    db: Session,
    digest_date: date,
    dry_run: bool = True,
    provider: EmailProvider | None = None,
) -> NewsletterResult:
    digest = get_digest_by_date(db=db, digest_date=digest_date)
    if digest is None:
        digest = generate_digest_for_date(db=db, digest_date=digest_date)

    subscriptions = db.execute(select(Subscription).where(Subscription.is_active.is_(True))).scalars().all()
    output_dir = Path("newsletter_dry_run") / digest_date.isoformat() if dry_run else None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    if not dry_run and provider is None:
        provider = build_email_provider()

    sent = 0
    for subscription in subscriptions:
        digest_md = _digest_for_subscription(db=db, digest=digest, subscription=subscription)
        unsubscribe_url = f"{settings.public_app_url.rstrip('/')}/unsubscribe?token={subscription.unsubscribe_token}"
        html = markdown.markdown(digest_md) + f"<hr><p><a href=\"{unsubscribe_url}\">Unsubscribe</a></p>"
        text = digest_md + f"\n\nUnsubscribe: {unsubscribe_url}"

        if dry_run and output_dir is not None:
            safe_email = subscription.email.replace("@", "_at_").replace(".", "_")
            (output_dir / f"{safe_email}.html").write_text(html, encoding="utf-8")
            sent += 1
            continue

        assert provider is not None
        provider.send(
            EmailMessage(
                from_email=settings.from_email,
                to_email=subscription.email,
                subject=f"AI Research Radar Digest - {digest_date.isoformat()}",
                html=html,
                text=text,
            )
        )
        sent += 1

    return NewsletterResult(
        date=digest_date,
        recipients_considered=len(subscriptions),
        recipients_sent=sent,
        dry_run=dry_run,
        output_dir=str(output_dir) if output_dir is not None else None,
    )


def _digest_for_subscription(db: Session, digest: Digest, subscription: Subscription) -> str:
    if not subscription.topic_ids:
        return digest.content_md

    topic_names = db.execute(select(Topic.name).where(Topic.id.in_(subscription.topic_ids))).scalars().all()
    if not topic_names:
        return digest.content_md

    lines = digest.content_md.splitlines()
    filtered_lines = [line for line in lines if not line.startswith("- ") or any(name.lower() in line.lower() for name in topic_names)]
    filtered_md = "\n".join(filtered_lines).strip()
    return filtered_md if filtered_md else digest.content_md


def _fetch_documents(db: Session, start_dt: datetime, end_dt: datetime) -> list[Document]:
    stmt = (
        select(Document)
        .where(
            and_(
                Document.published_at >= start_dt,
                Document.published_at < end_dt,
                Document.source.in_(["arxiv", "hackernews"]),
            )
        )
        .order_by(Document.published_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def _fetch_document_topic_map(db: Session, document_ids: list[UUID]) -> dict[UUID, str]:
    if not document_ids:
        return {}

    rows = db.execute(
        select(DocumentTopic.document_id, Topic.name, DocumentTopic.confidence)
        .join(Topic, Topic.id == DocumentTopic.topic_id)
        .where(DocumentTopic.document_id.in_(document_ids))
        .order_by(DocumentTopic.confidence.desc())
    ).all()

    topic_map: dict[UUID, str] = {}
    for document_id, topic_name, _confidence in rows:
        if document_id not in topic_map:
            topic_map[document_id] = topic_name
    return topic_map


def _hn_velocity_score(doc: Document, window_end: datetime) -> float:
    metadata = doc.metadata_json if isinstance(doc.metadata_json, dict) else {}
    score = float(metadata.get("score", 0) or 0)
    age_hours = max(1.0, (window_end - doc.published_at).total_seconds() / 3600)
    return score / age_hours


def _source_counts(docs: list[Document]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for doc in docs:
        counts[doc.source] = counts.get(doc.source, 0) + 1
    return counts


def _render_digest_markdown(
    digest_date: date,
    top_papers: list[Document],
    top_discussions: list[Document],
    topic_counts: dict[str, int],
    stats: dict,
) -> str:
    lines = [
        f"# AI Research Radar Digest - {digest_date.isoformat()}",
        "",
        "## Top papers",
    ]
    if top_papers:
        for paper in top_papers:
            lines.append(f"- [{paper.title}]({paper.url})")
    else:
        lines.append("- No new papers in this window.")

    lines.extend(["", "## Top discussions"])
    if top_discussions:
        for discussion in top_discussions:
            metadata = discussion.metadata_json if isinstance(discussion.metadata_json, dict) else {}
            score = metadata.get("score", 0)
            lines.append(f"- [{discussion.title}]({discussion.url}) (score: {score})")
    else:
        lines.append("- No new discussions in this window.")

    lines.extend(["", "## Topic highlights"])
    if topic_counts:
        for topic_name, count in sorted(topic_counts.items(), key=lambda kv: kv[1], reverse=True):
            lines.append(f"- {topic_name}: {count}")
    else:
        lines.append("- No topic highlights yet.")

    lines.extend(["", "## Stats", "```json", json.dumps(stats, indent=2, default=str), "```", ""])
    return "\n".join(lines)


def _upsert_digest(db: Session, digest_date: date, content_md: str, stats: dict) -> Digest:
    digest = db.execute(select(Digest).where(Digest.date == digest_date)).scalar_one_or_none()
    if digest is None:
        digest = Digest(date=digest_date, content_md=content_md, stats=stats)
        db.add(digest)
    else:
        digest.content_md = content_md
        digest.stats = stats
    db.commit()
    db.refresh(digest)
    return digest
