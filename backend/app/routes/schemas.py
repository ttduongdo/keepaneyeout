from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, RootModel


class TopicRef(BaseModel):
    id: UUID
    name: str


class TopicSummary(BaseModel):
    id: UUID
    name: str
    description: str


class SearchResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    title: str
    url: str
    source: str
    published_at: datetime
    snippet: str
    score: float
    topic_match: bool


class SearchResponse(BaseModel):
    active_topic: TopicRef | None = None
    results: list[SearchResult]


class AskRequest(BaseModel):
    query: str
    k: int = 8
    topic: str | None = None


class Citation(BaseModel):
    document_id: UUID
    title: str
    url: str
    chunk_id: UUID
    snippet: str
    topic_match: bool


class AskResponse(BaseModel):
    active_topic: TopicRef | None = None
    answer: str
    citations: list[Citation]


class ReimplementConstraints(BaseModel):
    time_hours: int | None = None
    compute: str | None = None


class ReimplementRequest(BaseModel):
    topic: str | None = None
    paper_id: str | None = None
    goal: str
    constraints: ReimplementConstraints | None = None
    k: int = 10


class BuilderCitation(BaseModel):
    document_id: UUID
    title: str
    url: str
    source: str
    chunk_id: UUID
    snippet: str


class ReimplementResponse(BaseModel):
    plan_md: str
    citations: list[BuilderCitation]


class CompareSelector(BaseModel):
    topic: str | None = None
    paper_id: str | None = None


class CompareRequest(BaseModel):
    a: CompareSelector
    b: CompareSelector
    constraints: ReimplementConstraints | None = None
    k: int = 8


class CompareResponse(BaseModel):
    comparison_md: str
    citations: list[BuilderCitation]


class SubscriptionRequest(BaseModel):
    email: str
    topic_ids: list[UUID] = Field(default_factory=list)
    frequency: str = "daily"


class SubscriptionResponse(BaseModel):
    id: UUID
    email: str
    topic_ids: list[UUID]
    frequency: str
    is_active: bool
    created_at: datetime


class DigestResponse(BaseModel):
    id: UUID
    date: str
    content_md: str
    stats: dict
    created_at: datetime


class AuthRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: UUID
    email: str
    topics: list[str]


class UserTopicsRequest(BaseModel):
    topics: list[str]


class UserTopicUpdateRequest(BaseModel):
    topic: str | None = None
    topics: list[str] | None = None


class BoardResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime


class BoardCreateRequest(BaseModel):
    name: str


class BoardPaperRequest(BaseModel):
    paper_id: UUID


class BoardPostRequest(BaseModel):
    post_id: UUID


class PaperFeedItem(BaseModel):
    id: UUID
    title: str
    authors: list[str] | str
    summary: str
    tags: list[str]
    published_date: datetime
    url: str | None = None


class PaperFeedResponse(BaseModel):
    items: list[PaperFeedItem]
    page: int
    has_more: bool


class PaperDetailResponse(BaseModel):
    id: UUID
    title: str
    authors: list[str] | str
    summary: str
    summary_full: str
    abstract: str
    tags: list[str]
    published_date: datetime
    url: str | None = None


class TrendSummaryResponse(BaseModel):
    summary_md: str


class PostResponse(BaseModel):
    id: UUID
    title: str
    summary: str | None = None
    source: str
    authors: list[str]
    url: str | None = None
    published_at: datetime
    ingested_at: datetime
    thumbnail_url: str | None = None
    topic_cluster: str | None = None
    topics: list[str] = Field(default_factory=list)


class PostFeedResponse(BaseModel):
    items: list[PostResponse]
    page: int
    has_more: bool


class TrendTopicResponse(BaseModel):
    topic: str
    size: int
    growth_rate: float
    posts: list[dict]


class TrendTimeseriesResponse(RootModel[dict[str, list[dict]]]):
    pass
