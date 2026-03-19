from __future__ import annotations

from pathlib import Path
from typing import Mapping
import logging

import httpx
from bs4 import BeautifulSoup

from app.models import Document

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
THUMBNAIL_DIR = STATIC_DIR / "thumbnails"
IMAGE_DIR = STATIC_DIR / "images"

FALLBACKS: Mapping[str, str] = {
    "ml": "/static/images/ml.svg",
    "robotics": "/static/images/robotics.svg",
    "security": "/static/images/security.svg",
    "audio": "/static/images/audio.svg",
}


def get_thumbnail_for_post(post: Document) -> str:
    if post.source == "arxiv":
        thumb = _thumbnail_from_arxiv(post)
        if thumb:
            return thumb
    if post.source == "hackernews":
        thumb = _thumbnail_from_hn(post)
        if thumb:
            return thumb
    return _fallback_thumbnail(post)


def _thumbnail_from_arxiv(post: Document) -> str | None:
    metadata = post.metadata_json if isinstance(post.metadata_json, dict) else {}
    arxiv_id = metadata.get("arxiv_id") or post.external_id
    if not arxiv_id:
        logger.info("No arXiv id found for thumbnail generation")
        return None

    try:
        import fitz  # PyMuPDF
    except Exception:
        logger.warning("PyMuPDF not available; skipping arXiv thumbnail generation")
        return None

    url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    try:
        logger.info("Downloading arXiv PDF for %s", arxiv_id)
        response = httpx.get(url, timeout=30.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Failed to download arXiv PDF for %s: %s", arxiv_id, exc)
        return None

    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
    output_path = THUMBNAIL_DIR / f"{arxiv_id}.png"

    try:
        with fitz.open(stream=response.content, filetype="pdf") as pdf:
            if pdf.page_count == 0:
                logger.info("arXiv PDF has no pages for %s", arxiv_id)
                return None
            page = pdf.load_page(0)
            images = page.get_images(full=True)
            if not images:
                logger.info("No figure found in first page for %s", arxiv_id)
                return None
            xref = images[0][0]
            pix = fitz.Pixmap(pdf, xref)
            if pix.alpha:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            pix.save(output_path)
    except Exception as exc:
        logger.warning("Failed to extract figure for %s: %s", arxiv_id, exc)
        return None

    logger.info("Extracted first figure for %s", arxiv_id)

    return f"/static/thumbnails/{output_path.name}"


def _thumbnail_from_hn(post: Document) -> str | None:
    if not post.url:
        logger.info("Hacker News post missing URL; skipping OG image")
        return None
    try:
        logger.info("Fetching OG image for %s", post.url)
        response = httpx.get(post.url, timeout=15.0, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError:
        logger.warning("Failed to fetch OG image for %s", post.url)
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    og = soup.find("meta", attrs={"property": "og:image"})
    if og and og.get("content"):
        logger.info("OG image detected for %s", post.url)
        return str(og.get("content"))
    logger.info("No OG image detected for %s", post.url)
    return None


def _fallback_thumbnail(post: Document) -> str:
    logger.info("No thumbnail found for %s, using fallback", post.title)
    title = post.title.lower()
    if "robot" in title:
        return FALLBACKS["robotics"]
    if "audio" in title or "speech" in title:
        return FALLBACKS["audio"]
    if "security" in title or "attack" in title:
        return FALLBACKS["security"]
    return FALLBACKS["ml"]
