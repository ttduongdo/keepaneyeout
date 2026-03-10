from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import BuilderCitation, CompareResponse, ReimplementResponse


client = TestClient(app)


def _citation() -> BuilderCitation:
    return BuilderCitation(
        document_id=uuid4(),
        title="Test Doc",
        url="https://example.com/doc",
        source="arxiv",
        chunk_id=uuid4(),
        snippet="snippet",
    )


def test_reimplement_happy_path(monkeypatch) -> None:
    def fake_reimplement_brief(db, payload):  # noqa: ANN001
        return ReimplementResponse(
            plan_md="# Plan\n\n## Overview\n- grounded",
            citations=[_citation(), _citation()],
        )

    monkeypatch.setattr("app.main.reimplement_brief", fake_reimplement_brief)

    response = client.post(
        "/reimplement",
        json={
            "topic": "RAG",
            "goal": "reproduce baseline results",
            "constraints": {"time_hours": 6, "compute": "single_gpu"},
            "k": 10,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "plan_md" in data
    assert len(data["citations"]) >= 2


def test_compare_happy_path(monkeypatch) -> None:
    def fake_compare_brief(db, payload):  # noqa: ANN001
        return CompareResponse(
            comparison_md=(
                "Summary\n\n| Dimension | A | B |\n|---|---|---|\n"
                "| method | retriever | agent |\n\nWhich to implement first: A"
            ),
            citations=[_citation(), _citation()],
        )

    monkeypatch.setattr("app.main.compare_brief", fake_compare_brief)

    response = client.post(
        "/compare",
        json={
            "a": {"topic": "RAG"},
            "b": {"topic": "Agents"},
            "k": 8,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "| Dimension | A | B |" in data["comparison_md"]
    assert len(data["citations"]) >= 2
