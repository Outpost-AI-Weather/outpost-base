"""Print the full stats payload for a given time."""

import argparse
import json
from datetime import datetime

from sqlmodel import Session

from outpost_base.db.session import engine
from outpost_base.stats.builder import build_stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--at", default="2026-01-15T12:00:00+00:00", help="UTC time, ISO 8601")
    parser.add_argument("--node", type=int, default=1)
    args = parser.parse_args()

    with Session(engine) as session:
        stats = build_stats(session, args.node, datetime.fromisoformat(args.at))

    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
