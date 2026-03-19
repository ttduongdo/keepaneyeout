from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))

from backend.scripts.ingestion._env import load_project_env  # noqa: E402

load_project_env()

from app.db import SessionLocal  # noqa: E402
from app.services.trend_service import update_trends  # noqa: E402


def main() -> None:
    with SessionLocal() as db:
        results = update_trends(db)
    print("Trend update complete")
    for item in results:
        print(f"- {item['topic']}: size={item['size']} growth_rate={item['growth_rate']:.2f}")


if __name__ == "__main__":
    main()
