from __future__ import annotations

import argparse
import time
from datetime import UTC, datetime
from pathlib import Path
import sys

import praw
from praw.models import Comment, Submission
from prawcore.exceptions import RequestException, ResponseException, TooManyRequests

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))

from scripts.ingestion._env import load_project_env  # noqa: E402

load_project_env()

from app.services.config import settings  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.services.ingest_utils import document_exists, insert_document_with_chunks  # noqa: E402
from app.models import Document  # noqa: E402

SUBREDDITS = ("MachineLearning", "LocalLLaMA")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest top Reddit posts into Postgres/pgvector")
    parser.add_argument("--max_posts", type=int, default=25, help="Top posts per subreddit")
    parser.add_argument("--time_filter", default="day", choices=["hour", "day", "week", "month", "year", "all"])
    parser.add_argument("--include_comments", action="store_true", help="Include top 10 comments in embedded text")
    return parser.parse_args()


def build_reddit_client() -> praw.Reddit:
    if not settings.reddit_client_id or not settings.reddit_client_secret or not settings.reddit_user_agent:
        raise RuntimeError("Missing Reddit credentials. Set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT")

    return praw.Reddit(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        user_agent=settings.reddit_user_agent,
    )


def ingest_reddit(max_posts: int, time_filter: str = "day", include_comments: bool = False) -> tuple[int, int, int, int]:
    reddit = build_reddit_client()

    inserted_docs = 0
    inserted_chunks = 0
    skipped_duplicates = 0
    errors = 0

    with SessionLocal() as db:
        for subreddit_name in SUBREDDITS:
            try:
                submissions = _with_retry(
                    lambda: list(reddit.subreddit(subreddit_name).top(time_filter=time_filter, limit=max_posts))
                )
            except Exception as exc:
                errors += 1
                print(f"[error] failed fetching r/{subreddit_name}: {exc}")
                continue

            for submission in submissions:
                try:
                    external_id = submission.id
                    if document_exists(db, source="reddit", external_id=external_id):
                        skipped_duplicates += 1
                        continue

                    body = build_submission_text(submission=submission, include_comments=include_comments)
                    doc = Document(
                        source="reddit",
                        external_id=external_id,
                        title=submission.title,
                        url=submission.url,
                        published_at=datetime.fromtimestamp(submission.created_utc, tz=UTC),
                        metadata_json={
                            "subreddit": subreddit_name,
                            "score": submission.score,
                            "num_comments": submission.num_comments,
                            "author": str(submission.author) if submission.author else "[deleted]",
                            "permalink": f"https://reddit.com{submission.permalink}",
                        },
                    )

                    chunks_added = insert_document_with_chunks(db=db, doc=doc, text_to_embed=body)
                    inserted_docs += 1
                    inserted_chunks += chunks_added
                except Exception as exc:
                    db.rollback()
                    errors += 1
                    print(f"[error] failed processing submission {getattr(submission, 'id', 'unknown')}: {exc}")

    return inserted_docs, inserted_chunks, skipped_duplicates, errors


def build_submission_text(submission: Submission, include_comments: bool) -> str:
    title = _clean_text(submission.title)
    selftext = _clean_text(submission.selftext)

    parts = [f"Title: {title}"]
    if selftext:
        parts.append(f"Body: {selftext}")

    if include_comments:
        comment_texts = _get_top_comments(submission, limit=10)
        if comment_texts:
            parts.append("Top comments:\n" + "\n".join(f"- {comment}" for comment in comment_texts))

    # TODO(comment ingestion improvements): enrich with comment scores, threading, and stronger filtering.
    return "\n\n".join(parts)


def _get_top_comments(submission: Submission, limit: int) -> list[str]:
    try:
        submission.comment_sort = "top"
        _with_retry(lambda: submission.comments.replace_more(limit=0))
    except Exception:
        return []

    comments: list[str] = []
    for comment in submission.comments:
        if isinstance(comment, Comment):
            text = _clean_text(comment.body)
            if text:
                comments.append(text)
            if len(comments) >= limit:
                break
    return comments


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = value.strip()
    if not text or text in {"[deleted]", "[removed]"}:
        return ""
    return text


def _with_retry(fn, retries: int = 3, base_sleep: float = 1.0):
    for attempt in range(retries + 1):
        try:
            return fn()
        except (TooManyRequests, RequestException, ResponseException) as exc:
            if attempt >= retries:
                raise
            sleep_for = base_sleep * (2**attempt)
            print(f"[retry] reddit request failed ({exc}); sleeping {sleep_for:.1f}s")
            time.sleep(sleep_for)


# TODO(subreddit expansion): add configurable subreddit list and additional AI communities.
def main() -> None:
    args = parse_args()
    docs, chunks, skipped, errors = ingest_reddit(
        max_posts=args.max_posts,
        time_filter=args.time_filter,
        include_comments=args.include_comments,
    )
    print(
        "Ingestion summary: "
        f"inserted_docs={docs}, inserted_chunks={chunks}, skipped_duplicates={skipped}, errors={errors}"
    )


if __name__ == "__main__":
    main()
