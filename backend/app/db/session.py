from __future__ import annotations

from collections.abc import Generator

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.services.config import settings


def _normalize_db_url(url: str) -> str:
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url

def _should_use_nullpool(url: str) -> bool:
    if os.getenv("DB_USE_NULLPOOL", "").strip().lower() in {"1", "true", "yes"}:
        return True
    lowered = url.lower()
    return "pooler" in lowered or ":6543" in lowered


def _disable_prepared() -> bool:
    return os.getenv("DB_DISABLE_PREPARED", "").strip().lower() in {"1", "true", "yes"}


db_url = _normalize_db_url(settings.database_url)
connect_args = {
    "prepare_threshold": 0,
}

use_nullpool = _should_use_nullpool(db_url)

engine_kwargs = {
    "future": True,
    "connect_args": connect_args,
}
if use_nullpool:
    engine_kwargs["poolclass"] = NullPool

engine = create_engine(db_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
