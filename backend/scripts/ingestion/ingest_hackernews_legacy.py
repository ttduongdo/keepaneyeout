from __future__ import annotations

import argparse
import time
from datetime import UTC, datetime
from pathlib import Path
import sys

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))

from scripts.ingestion._env import load_project_env  # noqa: E402

load_project_env()

from app.db import SessionLocal  # noqa: E402
from app.services.ingest_utils import document_exists, insert_document_with_chunks  # noqa: E402
from app.models import Document  # noqa: E402

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"
STORY_LISTS = {"topstories", "newstories", "beststories"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest Hacker News stories into Postgres/pgvector")
    parser.add_argument("--list", dest="list_name", default="topstories", choices=sorted(STORY_LISTS))
    parser.add_argument("--max_items", type=int, default=50)
    parser.add_argument("--min_score", type=int, default=0)
    parser.add_argument("--include_comments", type=_parse_bool, default=False)
    parser.add_argument("--max_comments", type=int, default=0)
    return parser.parse_args()


def ingest_hackernews(
    list_name: str,
    max_items: int,
    min_score: int = 0,
    include_comments: bool = False,
    max_comments: int = 0,
) -> tuple[int, int, int, int, int]:
    inserted_docs = 0
    inserted_chunks = 0
    skipped_duplicates = 0
    skipped_invalid = 0
    errors = 0

    with SessionLocal() as db:
        try:
            story_ids = _fetch_story_ids(list_name)[:max_items]
        except Exception as exc:
            print(f"[error] failed to fetch HN list '{list_name}': {exc}")
            return 0, 0, 0, 0, 1

        for story_id in story_ids:
            try:
                item = _fetch_item(story_id)
            except Exception as exc:
                errors += 1
                print(f"[error] failed fetching item {story_id}: {exc}")
                continue

            if not item or item.get("type") != "story":
                skipped_invalid += 1
                continue
            if item.get("deleted") or item.get("dead"):
                skipped_invalid += 1
                continue

            title = _clean_text(item.get("title"))
            if not title:
                skipped_invalid += 1
                continue
            if int(item.get("score") or 0) < min_score:
                skipped_invalid += 1
                continue

            external_id = str(item.get("id"))
            if document_exists(db, source="hackernews", external_id=external_id):
                skipped_duplicates += 1
                continue

            try:
                story_url = item.get("url") or f"https://news.ycombinator.com/item?id={external_id}"
                published_at = datetime.fromtimestamp(int(item.get("time", 0) or 0), tz=UTC)

                text_to_embed = _build_story_text(item, include_comments=include_comments, max_comments=max_comments)
                if not text_to_embed:
                    skipped_invalid += 1
                    continue

                doc = Document(
                    source="hackernews",
                    external_id=external_id,
                    title=title,
                    url=story_url,
                    published_at=published_at,
                    metadata_json={
                        "by": item.get("by"),
                        "score": item.get("score"),
                        "descendants": item.get("descendants"),
                        "type": item.get("type"),
                        "list_name": list_name,
                    },
                )
                chunks_added = insert_document_with_chunks(db=db, doc=doc, text_to_embed=text_to_embed)
                inserted_docs += 1
                inserted_chunks += chunks_added
            except Exception as exc:
                db.rollback()
                errors += 1
                print(f"[error] failed processing item {story_id}: {exc}")

    return inserted_docs, inserted_chunks, skipped_duplicates, skipped_invalid, errors


def _fetch_story_ids(list_name: str) -> list[int]:
    url = f"{HN_API_BASE}/{list_name}.json"
    response = _with_retry(lambda: httpx.get(url, timeout=20.0, follow_redirects=True))
    response.raise_for_status()
    payload = response.json()
    return [int(item_id) for item_id in payload if isinstance(item_id, int)]


def _fetch_item(item_id: int) -> dict | None:
    url = f"{HN_API_BASE}/item/{item_id}.json"
    response = _with_retry(lambda: httpx.get(url, timeout=20.0, follow_redirects=True))
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, dict) else None


def _build_story_text(item: dict, include_comments: bool, max_comments: int) -> str:
    title = _clean_text(item.get("title"))
    body = _strip_html(item.get("text", ""))

    sections = [f"Title: {title}"]
    if body:
        sections.append(f"Body: {body}")

    if include_comments and max_comments > 0:
        comment_texts = _fetch_top_level_comments(item, max_comments=max_comments)
        if comment_texts:
            sections.append("Top comments:\n" + "\n".join(f"- {text}" for text in comment_texts))

    # TODO(URL content extraction for HN links): fetch and embed linked article bodies when available.
    return "\n\n".join(sections)


def _fetch_top_level_comments(item: dict, max_comments: int) -> list[str]:
    comment_ids = item.get("kids")
    if not isinstance(comment_ids, list):
        return []

    comments: list[str] = []
    for kid in comment_ids[:max_comments]:
        if not isinstance(kid, int):
            continue
        try:
            comment = _fetch_item(kid)
        except Exception:
            continue
        if not comment or comment.get("type") != "comment":
            continue
        if comment.get("deleted") or comment.get("dead"):
            continue

        text = _strip_html(comment.get("text", ""))
        if text:
            comments.append(text)

    return comments


def _strip_html(value: str) -> str:
    if not value:
        return ""
    text = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    return _clean_text(text)


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = " ".join(str(value).split())
    if text in {"[deleted]", "[removed]"}:
        return ""
    return text


def _with_retry(fn, retries: int = 3, base_sleep: float = 1.0):
    for attempt in range(retries + 1):
        try:
            return fn()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            if attempt >= retries:
                raise
            sleep_for = base_sleep * (2**attempt)
            print(f"[retry] HN request failed ({exc}); sleeping {sleep_for:.1f}s")
            time.sleep(sleep_for)


def _parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError("Expected boolean value for --include_comments")


# TODO(weekly clustering): add scheduled clustering over embeddings.
# TODO(daily digest): generate a daily cited digest from recent documents.
def main() -> None:
    args = parse_args()
    docs, chunks, skipped_dup, skipped_invalid, errors = ingest_hackernews(
        list_name=args.list_name,
        max_items=args.max_items,
        min_score=args.min_score,
        include_comments=args.include_comments,
        max_comments=args.max_comments,
    )
    print(
        "Ingestion summary: "
        f"inserted_docs={docs}, inserted_chunks={chunks}, skipped_duplicates={skipped_dup}, "
        f"skipped_invalid={skipped_invalid}, errors={errors}"
    )


if __name__ == "__main__":
    main()
