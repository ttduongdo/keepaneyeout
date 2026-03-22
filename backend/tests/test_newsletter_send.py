from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from app.services.newsletter import send_newsletters_for_date


class DummyResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class FakeDB:
    def __init__(self, subscriptions):
        self.subscriptions = subscriptions

    def execute(self, stmt):  # noqa: ANN001
        return DummyResult(self.subscriptions)


class ProviderMock:
    def __init__(self):
        self.messages = []

    def send(self, message):  # noqa: ANN001
        self.messages.append(message)
        return "sent-1"


def test_send_newsletters_calls_provider_with_unsubscribe(monkeypatch) -> None:
    sub = SimpleNamespace(
        id=uuid4(),
        email="reader@example.com",
        topic_ids=[],
        frequency="daily",
        is_active=True,
        unsubscribe_token="abc123",
    )
    digest = SimpleNamespace(
        date=date(2026, 2, 23),
        content_md="# Digest\n\n- item",
        stats={"source_counts": {"arxiv": 1}},
    )

    monkeypatch.setattr("app.services.newsletter.get_digest_by_date", lambda db, digest_date: digest)

    provider = ProviderMock()
    result = send_newsletters_for_date(
        db=FakeDB([sub]),
        digest_date=date(2026, 2, 23),
        dry_run=False,
        provider=provider,
    )

    assert result.recipients_sent == 1
    assert len(provider.messages) == 1
    message = provider.messages[0]
    assert isinstance(message.from_email, str)
    assert message.to_email == "reader@example.com"
    assert message.subject == "Pinsight Digest - 2026-02-23"
    assert "unsubscribe?token=abc123" in message.html
    assert "unsubscribe?token=abc123" in message.text


def test_send_newsletters_dry_run_writes_html(monkeypatch, tmp_path) -> None:
    sub = SimpleNamespace(
        id=uuid4(),
        email="dryrun@example.com",
        topic_ids=[],
        frequency="daily",
        is_active=True,
        unsubscribe_token="drytoken",
    )
    digest = SimpleNamespace(
        date=date(2026, 2, 23),
        content_md="# Digest\n\n- item",
        stats={"source_counts": {"arxiv": 1}},
    )
    monkeypatch.setattr("app.services.newsletter.get_digest_by_date", lambda db, digest_date: digest)
    monkeypatch.chdir(tmp_path)

    result = send_newsletters_for_date(
        db=FakeDB([sub]),
        digest_date=date(2026, 2, 23),
        dry_run=True,
        provider=None,
    )

    assert result.dry_run is True
    assert result.recipients_sent == 1
    assert result.output_dir is not None
    html_files = list((tmp_path / "newsletter_dry_run" / "2026-02-23").glob("*.html"))
    assert len(html_files) == 1
    html = html_files[0].read_text(encoding="utf-8")
    assert "unsubscribe?token=drytoken" in html
