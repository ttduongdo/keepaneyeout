from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session

from app.services.auth import create_access_token, get_current_user, get_current_user_optional, hash_password, oauth_exchange_code, oauth_fetch_profile, verify_password
from app.services.builder import compare_brief, reimplement_brief
from app.services.config import settings
from app.db import get_db
from app.models import Board, BoardPaper, Document, DocumentTopic, Topic, User, UserTopic
from app.services.newsletter import get_digest_by_date, list_digests, unsubscribe_subscription, upsert_subscription
from app.services.openai_client import OpenAIServiceError
from app.services.papers_service import fetch_feed, generate_trend_summary, get_document_tags, get_paper_detail, get_related_papers, get_user_topics
from app.services.rag import ask_question, semantic_search
from app.routes.schemas import (
    AuthRequest,
    AuthResponse,
    AskRequest,
    AskResponse,
    BoardCreateRequest,
    BoardPaperRequest,
    BoardPostRequest,
    BoardResponse,
    CompareRequest,
    CompareResponse,
    DigestResponse,
    MeResponse,
    PaperFeedResponse,
    PaperFeedItem,
    PaperDetailResponse,
    PostFeedResponse,
    PostResponse,
    ReimplementRequest,
    ReimplementResponse,
    SearchResponse,
    SubscriptionRequest,
    SubscriptionResponse,
    TopicSummary,
    TrendSummaryResponse,
    TrendTopicResponse,
    UserTopicUpdateRequest,
    UserTopicsRequest,
)
from app.services.trend_service import get_trend_timeseries, get_trends

app = FastAPI(title="AI Research Radar API")

app.mount("/static", StaticFiles(directory=str(Path(__file__).resolve().parents[1] / "static")), name="static")

origins = [settings.frontend_url] if settings.frontend_url else []
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/signup", response_model=AuthResponse)
def signup(payload: AuthRequest, db: Session = Depends(get_db)) -> AuthResponse:
    existing = db.execute(select(User).where(User.email == payload.email.lower())).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=payload.email.lower(), password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user)
    return AuthResponse(access_token=token)


@app.post("/auth/login", response_model=AuthResponse)
def login(payload: AuthRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.execute(select(User).where(User.email == payload.email.lower())).scalar_one_or_none()
    if user is None or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user)
    return AuthResponse(access_token=token)


@app.post("/auth/logout")
def logout() -> dict[str, bool]:
    return {"success": True}


@app.get("/auth/google/login")
def google_login() -> dict[str, str]:
    if not settings.google_client_id:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    query = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={settings.google_client_id}"
        f"&redirect_uri={settings.google_redirect_uri}"
        "&response_type=code&scope=openid%20email%20profile"
    )
    return {"url": query}


@app.get("/auth/google/callback", response_model=AuthResponse)
def google_callback(code: str, db: Session = Depends(get_db)) -> AuthResponse:
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    token_payload = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }
    token_resp = oauth_exchange_code("https://oauth2.googleapis.com/token", token_payload)
    access_token = token_resp.get("access_token", "")
    if not access_token:
        raise HTTPException(status_code=401, detail="Google OAuth failed")
    profile = oauth_fetch_profile("https://www.googleapis.com/oauth2/v2/userinfo", access_token)
    email = profile.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Google OAuth missing email")

    user = db.execute(select(User).where(User.email == email.lower())).scalar_one_or_none()
    if user is None:
        user = User(email=email.lower(), password_hash=None)
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(user)
    return AuthResponse(access_token=token)


@app.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> MeResponse:
    topics = get_user_topics(db=db, user=current_user)
    return MeResponse(id=current_user.id, email=current_user.email, topics=topics)


@app.get("/user/topics", response_model=UserTopicsRequest)
def get_topics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserTopicsRequest:
    topics = get_user_topics(db=db, user=current_user)
    return UserTopicsRequest(topics=topics)


@app.post("/user/topics", response_model=UserTopicsRequest)
def set_topics(payload: UserTopicUpdateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserTopicsRequest:
    if payload.topics is not None:
        db.query(UserTopic).filter(UserTopic.user_id == current_user.id).delete()
        for topic in payload.topics:
            db.add(UserTopic(user_id=current_user.id, topic=topic))
        db.commit()
        return UserTopicsRequest(topics=payload.topics)
    if payload.topic:
        existing = db.execute(
            select(UserTopic).where(UserTopic.user_id == current_user.id, UserTopic.topic == payload.topic)
        ).scalar_one_or_none()
        if existing is None:
            db.add(UserTopic(user_id=current_user.id, topic=payload.topic))
            db.commit()
        topics = get_user_topics(db=db, user=current_user)
        return UserTopicsRequest(topics=topics)
    raise HTTPException(status_code=422, detail="Missing topic payload")


@app.delete("/user/topics/{topic}", response_model=UserTopicsRequest)
def delete_topic(topic: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserTopicsRequest:
    db.query(UserTopic).filter(UserTopic.user_id == current_user.id, UserTopic.topic == topic).delete()
    db.commit()
    topics = get_user_topics(db=db, user=current_user)
    return UserTopicsRequest(topics=topics)


@app.get("/papers/feed", response_model=PaperFeedResponse)
def papers_feed(
    section: str = Query("recommended"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=50),
    topics: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaperFeedResponse:
    topic_list = topics.split(",") if topics else get_user_topics(db=db, user=current_user)
    return fetch_feed(db=db, section=section, page=page, page_size=page_size, topics=topic_list)


@app.get("/papers/trends", response_model=TrendSummaryResponse)
def papers_trends(db: Session = Depends(get_db)) -> TrendSummaryResponse:
    try:
        return generate_trend_summary(db=db)
    except OpenAIServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _to_post_response(db: Session, doc: Document) -> PostResponse:
    return PostResponse(
        id=doc.id,
        title=doc.title,
        summary=doc.summary,
        source=doc.source,
        authors=doc.authors,
        url=doc.url,
        published_at=doc.published_at,
        ingested_at=doc.ingested_at,
        thumbnail_url=doc.thumbnail_url,
        topic_cluster=doc.topic_cluster,
        topics=get_document_tags(db, doc),
    )


@app.get("/posts", response_model=PostFeedResponse)
def list_posts(
    board_id: str | None = Query(None),
    section: str | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=50),
    topic_cluster: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> PostFeedResponse:
    clusters = [item for item in (topic_cluster or "").split(",") if item]
    stmt = select(Document)
    if board_id:
        stmt = stmt.join(BoardPaper, BoardPaper.paper_id == Document.id).where(BoardPaper.board_id == board_id)
    if q:
        normalized = " ".join(q.lower().replace("-", " ").replace("_", " ").split())
        pattern = f"%{normalized}%"

        def normalize_col(col):
            return func.regexp_replace(
                func.regexp_replace(func.lower(col), r"[-_]+", " ", "g"), r"\s+", " ", "g"
            )

        stmt = (
            stmt.outerjoin(DocumentTopic, DocumentTopic.document_id == Document.id)
            .outerjoin(Topic, Topic.id == DocumentTopic.topic_id)
            .where(
                or_(
                    normalize_col(Document.title).ilike(pattern),
                    normalize_col(Document.summary).ilike(pattern),
                    normalize_col(Document.topic_cluster).ilike(pattern),
                    normalize_col(Topic.name).ilike(pattern),
                )
            )
            .distinct()
        )
    if clusters:
        stmt = stmt.where(Document.topic_cluster.in_(clusters))
    if board_id or q:
        rows = db.execute(stmt.order_by(Document.published_at.desc()).offset((page - 1) * page_size).limit(page_size + 1)).scalars().all()
        has_more = len(rows) > page_size
        docs = rows[:page_size]
        return PostFeedResponse(items=[_to_post_response(db, doc) for doc in docs], page=page, has_more=has_more)

    if section:
        topics = get_user_topics(db=db, user=current_user) if current_user is not None else []
        feed = fetch_feed(db=db, section=section, page=page, page_size=page_size, topics=topics)
        ids = [item.id for item in feed.items]
        docs = db.execute(select(Document).where(Document.id.in_(ids))).scalars().all()
        doc_by_id = {str(doc.id): doc for doc in docs}
        ordered = [doc_by_id[str(item_id)] for item_id in ids if str(item_id) in doc_by_id]
        items = [_to_post_response(db, doc) for doc in ordered]
        if clusters:
            items = [item for item in items if item.topic_cluster in clusters]
        return PostFeedResponse(items=items, page=feed.page, has_more=feed.has_more)

    stmt = select(Document)
    if clusters:
        stmt = stmt.where(Document.topic_cluster.in_(clusters))
    rows = db.execute(stmt.order_by(Document.published_at.desc()).offset((page - 1) * page_size).limit(page_size + 1)).scalars().all()
    has_more = len(rows) > page_size
    docs = rows[:page_size]
    return PostFeedResponse(items=[_to_post_response(db, doc) for doc in docs], page=page, has_more=has_more)


@app.get("/papers/{paper_id}", response_model=PaperDetailResponse)
def paper_detail(paper_id: str, db: Session = Depends(get_db)) -> PaperDetailResponse:
    detail = get_paper_detail(db=db, paper_id=paper_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    return detail


@app.get("/papers/{paper_id}/related", response_model=list[PaperFeedItem])
def paper_related(paper_id: str, db: Session = Depends(get_db)) -> list[PaperFeedItem]:
    return get_related_papers(db=db, paper_id=paper_id)


@app.get("/trends", response_model=list[TrendTopicResponse])
def list_trends(db: Session = Depends(get_db)) -> list[TrendTopicResponse]:
    return [TrendTopicResponse(**item) for item in get_trends(db=db)]


@app.get("/trends/timeseries")
def trend_timeseries(range: str = Query("7d"), db: Session = Depends(get_db)) -> dict[str, list[dict]]:
    normalized = range.strip().lower()
    days = 7
    if normalized.endswith("h"):
        try:
            hours = int(normalized[:-1])
            days = max(1, int(hours / 24))
        except ValueError:
            days = 1
    elif normalized.endswith("d"):
        try:
            days = int(normalized[:-1])
        except ValueError:
            days = 7
    return get_trend_timeseries(db=db, days=days)


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


@app.get("/boards", response_model=list[BoardResponse])
def list_boards(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[BoardResponse]:
    boards = db.execute(select(Board).where(Board.user_id == current_user.id)).scalars().all()
    return [BoardResponse(id=board.id, name=board.name, created_at=board.created_at) for board in boards]


@app.post("/boards", response_model=BoardResponse)
def create_board(payload: BoardCreateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> BoardResponse:
    board = Board(user_id=current_user.id, name=payload.name)
    db.add(board)
    db.commit()
    db.refresh(board)
    return BoardResponse(id=board.id, name=board.name, created_at=board.created_at)


@app.post("/boards/{board_id}/papers")
def add_paper_to_board(board_id: str, payload: BoardPaperRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    board = db.execute(select(Board).where(Board.id == board_id, Board.user_id == current_user.id)).scalar_one_or_none()
    if board is None:
        raise HTTPException(status_code=404, detail="Board not found")
    doc = db.execute(select(Document).where(Document.id == payload.paper_id)).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    exists = db.execute(select(BoardPaper).where(BoardPaper.board_id == board.id, BoardPaper.paper_id == doc.id)).scalar_one_or_none()
    if exists is None:
        db.add(BoardPaper(board_id=board.id, paper_id=doc.id))
        db.commit()
    return {"status": "saved"}


@app.get("/boards/{board_id}/posts", response_model=list[PostResponse])
def list_board_posts(board_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[PostResponse]:
    board = db.execute(select(Board).where(Board.id == board_id, Board.user_id == current_user.id)).scalar_one_or_none()
    if board is None:
        raise HTTPException(status_code=404, detail="Board not found")
    rows = db.execute(
        select(Document).join(BoardPaper, BoardPaper.paper_id == Document.id).where(BoardPaper.board_id == board.id)
    ).scalars().all()
    return [_to_post_response(db, doc) for doc in rows]


@app.post("/boards/{board_id}/save_post")
def save_post_to_board(board_id: str, payload: BoardPostRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    board = db.execute(select(Board).where(Board.id == board_id, Board.user_id == current_user.id)).scalar_one_or_none()
    if board is None:
        raise HTTPException(status_code=404, detail="Board not found")
    doc = db.execute(select(Document).where(Document.id == payload.post_id)).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail="Post not found")
    exists = db.execute(select(BoardPaper).where(BoardPaper.board_id == board.id, BoardPaper.paper_id == doc.id)).scalar_one_or_none()
    if exists is None:
        db.add(BoardPaper(board_id=board.id, paper_id=doc.id))
        db.commit()
    return {"status": "saved"}


@app.get("/boards/{board_id}")
def get_board(board_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    board = db.execute(select(Board).where(Board.id == board_id, Board.user_id == current_user.id)).scalar_one_or_none()
    if board is None:
        raise HTTPException(status_code=404, detail="Board not found")
    rows = db.execute(
        select(Document).join(BoardPaper, BoardPaper.paper_id == Document.id).where(BoardPaper.board_id == board.id)
    ).scalars().all()
    return {
        "id": str(board.id),
        "name": board.name,
        "papers": [
            {
                "id": doc.id,
                "title": doc.title,
                "url": doc.url,
                "published_date": doc.published_at,
            }
            for doc in rows
        ],
    }
