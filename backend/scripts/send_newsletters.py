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
from app.services.newsletter import send_newsletters_for_date  # noqa: E402


def _parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError("Expected boolean value")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send newsletters for a digest date")
    parser.add_argument("--date", required=True, help="Digest date in YYYY-MM-DD")
    parser.add_argument("--dry_run", type=_parse_bool, default=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    digest_date = date.fromisoformat(args.date)

    with SessionLocal() as db:
        result = send_newsletters_for_date(db=db, digest_date=digest_date, dry_run=args.dry_run)

    print(
        "Newsletter summary: "
        f"date={result.date.isoformat()}, considered={result.recipients_considered}, "
        f"sent={result.recipients_sent}, dry_run={result.dry_run}, output_dir={result.output_dir}"
    )


if __name__ == "__main__":
    main()
