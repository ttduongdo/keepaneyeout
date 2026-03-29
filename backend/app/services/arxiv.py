from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import random
import time
from typing import Any
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

import httpx
from dateutil import parser as date_parser


ARXIV_API = "https://export.arxiv.org/api/query"


@dataclass
class ArxivPaper:
    external_id: str
    title: str
    abstract: str
    authors: list[str]
    categories: list[str]
    url: str
    published_at: datetime


def fetch_arxiv(query: str, max_results: int = 25) -> list[ArxivPaper]:
    url = f"{ARXIV_API}?search_query={quote_plus(query)}&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    def _request():
        response = httpx.get(
            url,
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "Pinsight/1.0"},
        )
        response.raise_for_status()
        return response

    resp = _with_retry(_request)

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(resp.text)

    papers: list[ArxivPaper] = []
    for entry in root.findall("atom:entry", ns):
        entry_id = _text(entry, "atom:id", ns)
        external_id = entry_id.rsplit("/", 1)[-1]
        title = _text(entry, "atom:title", ns).strip().replace("\n", " ")
        abstract = _text(entry, "atom:summary", ns).strip().replace("\n", " ")
        published = date_parser.parse(_text(entry, "atom:published", ns))

        authors = [
            author.find("atom:name", ns).text.strip()
            for author in entry.findall("atom:author", ns)
            if author.find("atom:name", ns) is not None and author.find("atom:name", ns).text
        ]
        categories = [category.attrib.get("term", "").strip() for category in entry.findall("atom:category", ns)]
        categories = [category for category in categories if category]

        papers.append(
            ArxivPaper(
                external_id=external_id,
                title=title,
                abstract=abstract,
                authors=authors,
                categories=categories,
                url=f"https://arxiv.org/abs/{external_id}",
                published_at=published,
            )
        )

    return papers


def _text(entry: ET.Element, path: str, ns: dict[str, Any]) -> str:
    el = entry.find(path, ns)
    return el.text if el is not None and el.text else ""


def _with_retry(fn, retries: int = 5, base_sleep: float = 1.5):
    for attempt in range(retries + 1):
        try:
            return fn()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status not in {429, 500, 502, 503, 504}:
                raise
            if attempt >= retries:
                raise
            retry_after = exc.response.headers.get("Retry-After") if exc.response is not None else None
            if retry_after and retry_after.isdigit():
                sleep_for = float(retry_after)
            else:
                sleep_for = base_sleep * (2**attempt)
            sleep_for += random.uniform(0, 0.5)
            print(f"[retry] arXiv request failed ({status}); sleeping {sleep_for:.1f}s")
            time.sleep(sleep_for)
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            if attempt >= retries:
                raise
            sleep_for = base_sleep * (2**attempt) + random.uniform(0, 0.5)
            print(f"[retry] arXiv request failed ({exc}); sleeping {sleep_for:.1f}s")
            time.sleep(sleep_for)
