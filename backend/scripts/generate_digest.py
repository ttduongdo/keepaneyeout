from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))

from scripts._env import load_project_env  # noqa: E402

load_project_env()

from app.db import SessionLocal  # noqa: E402
from app.services.newsletter import generate_digest_for_date  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate newsletter digest")
    parser.add_argument("--date", required=True, help="Digest date in YYYY-MM-DD")
    parser.add_argument("--frequency", default="daily", choices=["daily", "weekly"])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    digest_date = date.fromisoformat(args.date)

    with SessionLocal() as db:
        digest = generate_digest_for_date(db=db, digest_date=digest_date, frequency=args.frequency)

    print(
        "Digest summary: "
        f"date={digest.date.isoformat()}, chars={len(digest.content_md)}, stats_keys={list(digest.stats.keys())}"
    )


if __name__ == "__main__":
    main()
