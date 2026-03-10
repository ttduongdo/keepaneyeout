from __future__ import annotations

import argparse
from datetime import date

from app.db import SessionLocal
from app.newsletter import generate_digest_for_date


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
