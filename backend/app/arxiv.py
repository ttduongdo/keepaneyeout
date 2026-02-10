from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
    url: str
    published_at: datetime


def fetch_arxiv(query: str, max_results: int = 25) -> list[ArxivPaper]:
    url = f"{ARXIV_API}?search_query={quote_plus(query)}&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    resp = httpx.get(url, timeout=30.0, follow_redirects=True)
    resp.raise_for_status()

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

        papers.append(
            ArxivPaper(
                external_id=external_id,
                title=title,
                abstract=abstract,
                authors=authors,
                url=entry_id,
                published_at=published,
            )
        )

    return papers


def _text(entry: ET.Element, path: str, ns: dict[str, Any]) -> str:
    el = entry.find(path, ns)
    return el.text if el is not None and el.text else ""
