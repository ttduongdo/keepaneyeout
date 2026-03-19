from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Document, TrendTopic


def _load_recent_posts(db: Session, days: int = 14) -> list[Document]:
    cutoff = datetime.now(tz=UTC) - timedelta(days=days)
    return (
        db.execute(select(Document).where(Document.published_at >= cutoff).order_by(Document.published_at.desc()))
        .scalars()
        .all()
    )


def _cluster_embeddings(embeddings: list[list[float]]) -> list[int]:
    if len(embeddings) < 2:
        return [0 for _ in embeddings]
    k = min(8, max(2, len(embeddings) // 10))
    model = KMeans(n_clusters=k, n_init="auto", random_state=42)
    labels = model.fit_predict(np.array(embeddings))
    return labels.tolist()


def _extract_keywords(texts: list[str], labels: list[int]) -> dict[int, list[str]]:
    vectorizer = TfidfVectorizer(max_features=500, stop_words="english")
    tfidf = vectorizer.fit_transform(texts)
    terms = vectorizer.get_feature_names_out()

    keywords: dict[int, list[str]] = {}
    for label in set(labels):
        idx = [i for i, lab in enumerate(labels) if lab == label]
        if not idx:
            continue
        scores = tfidf[idx].mean(axis=0)
        top_indices = scores.A1.argsort()[::-1][:5]
        keywords[label] = [terms[i] for i in top_indices if scores.A1[i] > 0]
    return keywords


def update_trends(db: Session) -> list[dict[str, Any]]:
    docs = _load_recent_posts(db, days=14)
    docs = [doc for doc in docs if doc.embedding is not None]
    if not docs:
        return []

    embeddings = [doc.embedding for doc in docs if doc.embedding is not None]
    labels = _cluster_embeddings(embeddings)

    texts = [f"{doc.title} {doc.summary or ''}" for doc in docs]
    keywords = _extract_keywords(texts, labels)

    by_label: dict[int, list[Document]] = defaultdict(list)
    for doc, label in zip(docs, labels):
        by_label[label].append(doc)

    now = datetime.now(tz=UTC)
    week_start = now - timedelta(days=7)
    prev_start = now - timedelta(days=14)

    results: list[dict[str, Any]] = []
    db.query(TrendTopic).delete()

    for label, posts in by_label.items():
        topic_terms = keywords.get(label, [])
        topic = " ".join([term.title() for term in topic_terms[:2]]) or f"Cluster {label}"

        this_week = [p for p in posts if p.published_at >= week_start]
        last_week = [p for p in posts if prev_start <= p.published_at < week_start]
        growth_rate = len(this_week) / (len(last_week) + 1)

        db.add(
            TrendTopic(
                topic=topic,
                size=len(posts),
                growth_rate=growth_rate,
            )
        )

        for post in this_week:
            post.topic_cluster = topic

        representative = sorted(posts, key=lambda p: p.published_at, reverse=True)[:3]
        results.append(
            {
                "topic": topic,
                "size": len(posts),
                "growth_rate": growth_rate,
                "posts": [
                    {
                        "id": post.id,
                        "title": post.title,
                        "url": post.url,
                        "published_at": post.published_at,
                    }
                    for post in representative
                ],
            }
        )

    db.commit()
    return results


def get_trends(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(select(TrendTopic).order_by(TrendTopic.size.desc())).scalars().all()
    results: list[dict[str, Any]] = []
    for row in rows:
        posts = (
            db.execute(
                select(Document)
                .where(Document.topic_cluster == row.topic)
                .order_by(Document.published_at.desc())
                .limit(3)
            )
            .scalars()
            .all()
        )
        results.append(
            {
                "topic": row.topic,
                "size": row.size,
                "growth_rate": row.growth_rate,
                "posts": [
                    {
                        "id": post.id,
                        "title": post.title,
                        "url": post.url,
                        "published_at": post.published_at,
                    }
                    for post in posts
                ],
            }
        )
    return results


def get_trend_timeseries(db: Session, days: int = 7) -> dict[str, list[dict[str, Any]]]:
    cutoff = datetime.now(tz=UTC) - timedelta(days=days)
    rows = (
        db.execute(
            select(
                Document.topic_cluster,
                func.date(Document.published_at).label("day"),
                func.count(Document.id).label("count"),
            )
            .where(Document.published_at >= cutoff, Document.topic_cluster.isnot(None))
            .group_by(Document.topic_cluster, func.date(Document.published_at))
            .order_by(func.date(Document.published_at))
        )
        .all()
    )

    series: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for topic, day, count in rows:
        series[str(topic)].append({"date": str(day), "count": int(count)})

    return dict(series)
