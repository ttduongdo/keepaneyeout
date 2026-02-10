from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SearchResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    title: str
    url: str
    source: str
    published_at: datetime
    snippet: str
    score: float


class AskRequest(BaseModel):
    query: str
    k: int = 8


class Citation(BaseModel):
    document_id: UUID
    title: str
    url: str
    chunk_id: UUID
    snippet: str


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
