from __future__ import annotations

import argparse
import time
from datetime import UTC, datetime

import feedparser
import httpx
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from readability import Document as ReadabilityDocument

from app.config import settings
from app.db import SessionLocal
from app.ingest_utils import document_exists, insert_document_with_chunks
from app.models import Document

MEDIUM_FEEDS = {
    "AI": "https://medium.com/feed/tag/ai",
    "Machine Learning": "https://medium.com/feed/tag/machine-learning",
    "Deep Learning": "https://medium.com/feed/tag/deep-learning",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest Medium posts from tag RSS feeds")
    parser.add_argument("--max_posts", type=int, default=25, help="Max posts per feed")
    return parser.parse_args()


def ingest_medium(max_posts: int) -> tuple[int, int, int, int]:
    inserted_docs = 0
    inserted_chunks = 0
    skipped_duplicates = 0
    errors = 0

    with SessionLocal() as db:
        for feed_name, feed_url in MEDIUM_FEEDS.items():
            try:
                feed = feedparser.parse(feed_url)
            except Exception as exc:
                errors += 1
                print(f"[error] failed parsing feed {feed_name}: {exc}")
                continue

            entries = feed.entries[:max_posts]
            for entry in entries:
                try:
                    external_id = _entry_external_id(entry)
                    if not external_id:
                        errors += 1
                        print("[error] skipping Medium entry with missing external id")
                        continue
                    if document_exists(db, source="medium", external_id=external_id):
                        skipped_duplicates += 1
                        continue

                    text = _build_text(entry)
                    if not text:
                        errors += 1
                        print(f"[error] no readable text for entry: {external_id}")
                        continue

                    tags = [tag.term for tag in getattr(entry, "tags", []) if getattr(tag, "term", None)]
                    author = getattr(entry, "author", "") or "unknown"
                    url = getattr(entry, "link", "")
                    published_at = _entry_published_at(entry)

                    doc = Document(
                        source="medium",
                        external_id=external_id,
                        title=getattr(entry, "title", "Untitled"),
                        url=url,
                        published_at=published_at,
                        metadata_json={
                            "author": author,
                            "tags": tags,
                            "feed_name": feed_name,
                        },
                    )

                    chunks_added = insert_document_with_chunks(db=db, doc=doc, text_to_embed=text)
                    inserted_docs += 1
                    inserted_chunks += chunks_added
                except Exception as exc:
                    db.rollback()
                    errors += 1
                    print(f"[error] failed processing Medium entry: {exc}")

    return inserted_docs, inserted_chunks, skipped_duplicates, errors


def _entry_external_id(entry) -> str:
    return getattr(entry, "id", "") or getattr(entry, "guid", "") or getattr(entry, "link", "")


def _entry_published_at(entry) -> datetime:
    published = getattr(entry, "published", "") or getattr(entry, "updated", "")
    if published:
        return date_parser.parse(published).astimezone(UTC)
    return datetime.now(tz=UTC)


def _build_text(entry) -> str:
    title = _clean_text(getattr(entry, "title", ""))
    summary = _extract_feed_text(entry)
    url = getattr(entry, "link", "")

    full_text = ""
    if len(summary) < 600 and url:
        full_text = _extract_article_text(url)

    body = full_text if len(full_text) >= 400 else summary
    if not body:
        return ""

    return f"Title: {title}\n\nBody: {body}" if title else body


def _extract_feed_text(entry) -> str:
    content_items = getattr(entry, "content", []) or []
    for item in content_items:
        html = getattr(item, "value", "")
        text = _html_to_text(html)
        if len(text) >= 200:
            return text

    summary_html = getattr(entry, "summary", "") or getattr(entry, "description", "")
    return _html_to_text(summary_html)


def _extract_article_text(url: str) -> str:
    try:
        html = _with_retry(lambda: _fetch_html(url))
    except Exception:
        return ""

    try:
        readable_html = ReadabilityDocument(html).summary()
        return _html_to_text(readable_html)
    except Exception:
        return _html_to_text(html)


def _fetch_html(url: str) -> str:
    headers = {"User-Agent": settings.medium_user_agent}
    with httpx.Client(timeout=settings.medium_fetch_timeout_seconds, follow_redirects=True, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def _html_to_text(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return _clean_text(soup.get_text(" ", strip=True))


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = " ".join(value.split())
    return "" if text in {"[deleted]", "[removed]"} else text


def _with_retry(fn, retries: int = 2, base_sleep: float = 1.0):
    for attempt in range(retries + 1):
        try:
            return fn()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            if attempt >= retries:
                raise
            sleep_for = base_sleep * (2**attempt)
            print(f"[retry] medium fetch failed ({exc}); sleeping {sleep_for:.1f}s")
            time.sleep(sleep_for)


def main() -> None:
    args = parse_args()
    docs, chunks, skipped, errors = ingest_medium(max_posts=args.max_posts)
    print(
        "Ingestion summary: "
        f"inserted_docs={docs}, inserted_chunks={chunks}, skipped_duplicates={skipped}, errors={errors}"
    )


if __name__ == "__main__":
    main()
