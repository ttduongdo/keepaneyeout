from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


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
