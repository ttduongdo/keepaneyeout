from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_subscription_create_and_unsubscribe(monkeypatch) -> None:
    token = "token-123"

    def fake_upsert_subscription(db, email, topic_ids, frequency):  # noqa: ANN001
        return SimpleNamespace(
            id=uuid4(),
            email=email,
            topic_ids=topic_ids,
            frequency=frequency,
            is_active=True,
            unsubscribe_token=token,
            created_at=datetime.now(tz=UTC),
        )

    monkeypatch.setattr("app.routes.api.upsert_subscription", fake_upsert_subscription)
    monkeypatch.setattr("app.routes.api.unsubscribe_subscription", lambda db, token: token == "token-123")

    response = client.post(
        "/subscriptions",
        json={"email": "reader@example.com", "topic_ids": [], "frequency": "daily"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "reader@example.com"
    assert "unsubscribe_token" not in data

    unsub = client.get("/unsubscribe", params={"token": "token-123"})
    assert unsub.status_code == 200
    assert unsub.json() == {"status": "unsubscribed"}
