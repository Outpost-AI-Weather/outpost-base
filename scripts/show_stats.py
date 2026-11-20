"""Print stats for a given time, for checking the stats engine by hand."""

import argparse
import json
from datetime import datetime, timedelta

from sqlmodel import Session

from outpost_base.db.session import engine
from outpost_base.stats.engine import current_conditions, load_readings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--at", default="2026-01-15T12:00:00+00:00", help="UTC time, ISO 8601")
    parser.add_argument("--node", type=int, default=1)
    args = parser.parse_args()

    at = datetime.fromisoformat(args.at)
    with Session(engine) as session:
        df = load_readings(session, args.node, at - timedelta(days=8), at)

    print(json.dumps(current_conditions(df, at), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
