from __future__ import annotations

import argparse
from pathlib import Path
import sys

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))

from backend.scripts._env import load_project_env  # noqa: E402

load_project_env()

from app.db import SessionLocal  # noqa: E402
from app.models import Document  # noqa: E402
from app.services.thumbnail_service import get_thumbnail_for_post  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Debug thumbnail generation for recent posts")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--update", action="store_true", help="Update missing thumbnail_url values")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with SessionLocal() as db:
        docs = db.execute(select(Document).order_by(Document.ingested_at.desc()).limit(args.limit)).scalars().all()
        if not docs:
            print("No documents found.")
            return
        for doc in docs:
            thumbnail = get_thumbnail_for_post(doc)
            print(f"{doc.id} | {doc.title[:60]} | {thumbnail}")
            if args.update and thumbnail and doc.thumbnail_url != thumbnail:
                doc.thumbnail_url = thumbnail
        if args.update:
            db.commit()


if __name__ == "__main__":
    main()
