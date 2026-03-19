from __future__ import annotations

import time

import httpx
from bs4 import BeautifulSoup

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"
STORY_LISTS = {"topstories", "newstories", "beststories"}


def fetch_story_ids(list_name: str) -> list[int]:
    if list_name not in STORY_LISTS:
        raise ValueError(f"Unknown list: {list_name}")
    url = f"{HN_API_BASE}/{list_name}.json"
    response = _with_retry(lambda: httpx.get(url, timeout=20.0, follow_redirects=True))
    response.raise_for_status()
    payload = response.json()
    return [int(item_id) for item_id in payload if isinstance(item_id, int)]


def fetch_item(item_id: int) -> dict | None:
    url = f"{HN_API_BASE}/item/{item_id}.json"
    response = _with_retry(lambda: httpx.get(url, timeout=20.0, follow_redirects=True))
    response.raise_for_status()
    payload = response.json()
    return payload if isinstance(payload, dict) else None


def strip_html(value: str) -> str:
    if not value:
        return ""
    text = BeautifulSoup(value, "html.parser").get_text(" ", strip=True)
    return clean_text(text)


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = " ".join(str(value).split())
    if text in {"[deleted]", "[removed]"}:
        return ""
    return text


def with_retry(fn, retries: int = 3, base_sleep: float = 1.0):
    for attempt in range(retries + 1):
        try:
            return fn()
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            if attempt >= retries:
                raise
            sleep_for = base_sleep * (2**attempt)
            print(f"[retry] HN request failed ({exc}); sleeping {sleep_for:.1f}s")
            time.sleep(sleep_for)


def _with_retry(fn, retries: int = 3, base_sleep: float = 1.0):
    return with_retry(fn, retries=retries, base_sleep=base_sleep)
