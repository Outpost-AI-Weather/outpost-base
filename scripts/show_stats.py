"""Print stats for a given time, for checking the stats engine by hand."""

import argparse
import json
from datetime import datetime, timedelta

from sqlmodel import Session

from outpost_base.db.session import engine
from outpost_base.stats.engine import (
    compare_with_yesterday,
    current_conditions,
    load_readings,
)
from outpost_base.stats.trends import (
    data_quality,
    pressure_tendency,
    seven_day_trend,
    yesterday_temperature_range,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--at", default="2026-01-15T12:00:00+00:00", help="UTC time, ISO 8601")
    parser.add_argument("--node", type=int, default=1)
    args = parser.parse_args()

    at = datetime.fromisoformat(args.at)
    with Session(engine) as session:
        df = load_readings(session, args.node, at - timedelta(days=9), at)

    current = current_conditions(df, at)
    print(json.dumps(current, indent=2, ensure_ascii=False))

    if current:
        now = datetime.fromisoformat(current["measured_at"])
        for result in [
            compare_with_yesterday(df, now),
            seven_day_trend(df, now),
            yesterday_temperature_range(df, now),
            pressure_tendency(df, now),
            data_quality(df, now),
        ]:
            print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
