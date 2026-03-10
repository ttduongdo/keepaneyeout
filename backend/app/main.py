from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.builder import compare_brief, reimplement_brief
from app.config import settings
from app.db import get_db
from app.models import Topic
from app.newsletter import get_digest_by_date, list_digests, unsubscribe_subscription, upsert_subscription
from app.openai_client import OpenAIServiceError
from app.rag import ask_question, semantic_search
from app.schemas import (
    AskRequest,
    AskResponse,
    CompareRequest,
    CompareResponse,
    DigestResponse,
    ReimplementRequest,
    ReimplementResponse,
    SearchResponse,
    SubscriptionRequest,
    SubscriptionResponse,
    TopicSummary,
)

app = FastAPI(title="AI Research Radar API")

origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1),
    k: int = Query(10, ge=1, le=50),
    topic: str | None = Query(None),
    db: Session = Depends(get_db),
) -> SearchResponse:
    try:
        return semantic_search(db=db, query=q, k=k, topic=topic)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OpenAIServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, db: Session = Depends(get_db)) -> AskResponse:
    if payload.k < 1 or payload.k > 50:
        raise HTTPException(status_code=422, detail="k must be between 1 and 50")

    try:
        return ask_question(db=db, query=payload.query, k=payload.k, topic=payload.topic)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OpenAIServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/topics", response_model=list[TopicSummary])
def list_topics(db: Session = Depends(get_db)) -> list[TopicSummary]:
    topics = db.execute(select(Topic).order_by(Topic.name.asc())).scalars().all()
    return [TopicSummary(id=topic.id, name=topic.name, description=topic.description) for topic in topics]


# TODO(reimplementation mode endpoint): add an endpoint that returns topic-scoped source bundles for rebuild workflows.


@app.post("/reimplement", response_model=ReimplementResponse)
def reimplement(payload: ReimplementRequest, db: Session = Depends(get_db)) -> ReimplementResponse:
    try:
        return reimplement_brief(db=db, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OpenAIServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/compare", response_model=CompareResponse)
def compare(payload: CompareRequest, db: Session = Depends(get_db)) -> CompareResponse:
    try:
        return compare_brief(db=db, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OpenAIServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/subscriptions", response_model=SubscriptionResponse)
def create_subscription(payload: SubscriptionRequest, db: Session = Depends(get_db)) -> SubscriptionResponse:
    try:
        subscription = upsert_subscription(
            db=db,
            email=payload.email,
            topic_ids=payload.topic_ids,
            frequency=payload.frequency,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return SubscriptionResponse(
        id=subscription.id,
        email=subscription.email,
        topic_ids=subscription.topic_ids,
        frequency=subscription.frequency,
        is_active=subscription.is_active,
        created_at=subscription.created_at,
    )


@app.get("/digests", response_model=list[DigestResponse])
def get_digests(limit: int = Query(30, ge=1, le=100), db: Session = Depends(get_db)) -> list[DigestResponse]:
    digests = list_digests(db=db, limit=limit)
    return [
        DigestResponse(
            id=digest.id,
            date=digest.date.isoformat(),
            content_md=digest.content_md,
            stats=digest.stats,
            created_at=digest.created_at,
        )
        for digest in digests
    ]


@app.get("/digests/{digest_date}", response_model=DigestResponse)
def get_digest(digest_date: str, db: Session = Depends(get_db)) -> DigestResponse:
    try:
        from datetime import date

        parsed = date.fromisoformat(digest_date)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid date format. Use YYYY-MM-DD.") from exc

    digest = get_digest_by_date(db=db, digest_date=parsed)
    if digest is None:
        raise HTTPException(status_code=404, detail="Digest not found")

    return DigestResponse(
        id=digest.id,
        date=digest.date.isoformat(),
        content_md=digest.content_md,
        stats=digest.stats,
        created_at=digest.created_at,
    )


@app.get("/unsubscribe")
def unsubscribe(token: str = Query(..., min_length=8), db: Session = Depends(get_db)) -> dict[str, str]:
    success = unsubscribe_subscription(db=db, token=token)
    if not success:
        raise HTTPException(status_code=404, detail="Invalid unsubscribe token")
    return {"status": "unsubscribed"}
