from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.newsletter import generate_digest_for_date


def test_generate_digest_deterministic(monkeypatch) -> None:
    docs = [
        SimpleNamespace(
            id=uuid4(),
            source="arxiv",
            title="Fast RAG Baseline",
            url="https://arxiv.org/abs/1234.5678",
            published_at=datetime(2026, 2, 23, 8, 0, tzinfo=UTC),
            metadata_json={"score": 0},
        ),
        SimpleNamespace(
            id=uuid4(),
            source="hackernews",
            title="HN discussion on serving",
            url="https://news.ycombinator.com/item?id=1",
            published_at=datetime(2026, 2, 23, 9, 0, tzinfo=UTC),
            metadata_json={"score": 120},
        ),
    ]

    monkeypatch.setattr("app.newsletter._fetch_documents", lambda db, start_dt, end_dt: docs)
    monkeypatch.setattr("app.newsletter._fetch_document_topic_map", lambda db, document_ids: {docs[0].id: "RAG"})

    captured = {}

    def fake_upsert(db, digest_date, content_md, stats):  # noqa: ANN001
        captured["date"] = digest_date
        captured["content_md"] = content_md
        captured["stats"] = stats
        return SimpleNamespace(date=digest_date, content_md=content_md, stats=stats)

    monkeypatch.setattr("app.newsletter._upsert_digest", fake_upsert)

    digest = generate_digest_for_date(db=object(), digest_date=date(2026, 2, 23), frequency="daily")

    assert digest.date.isoformat() == "2026-02-23"
    assert "Fast RAG Baseline" in digest.content_md
    assert "HN discussion on serving" in digest.content_md
    assert captured["stats"]["source_counts"]["arxiv"] == 1
    assert captured["stats"]["source_counts"]["hackernews"] == 1
    assert "OPENAI_API_KEY" not in digest.content_md
    assert "RESEND_API_KEY" not in digest.content_md
