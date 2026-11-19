"""Load decoder-format JSON Lines readings into the database through ingest."""

import argparse
import json
from collections import Counter
from pathlib import Path

from sqlmodel import Session, SQLModel

from outpost_base.db.session import create_db_and_tables, engine
from outpost_base.ingest.ingest import ingest_reading


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON Lines file of decoder-format readings")
    parser.add_argument("--reset", action="store_true", help="clear all tables first")
    args = parser.parse_args()

    if args.reset:
        SQLModel.metadata.drop_all(engine)
    create_db_and_tables()

    statuses = Counter()
    rejected_reasons = Counter()
    nulled_fields = Counter()
    gap_events = 0
    missed_total = 0

    with Session(engine) as session:
        for line in Path(args.input).read_text().splitlines():
            if not line.strip():
                continue
            result = ingest_reading(session, json.loads(line))

            statuses[result.status] += 1
            if result.reason:
                rejected_reasons[result.reason] += 1
            for name in result.nulled_fields:
                nulled_fields[name] += 1
            if result.missed_packets:
                gap_events += 1
                missed_total += result.missed_packets

    print(f"Ingested {args.input}")
    print(f"  Saved:              {statuses['saved']}")
    print(f"  Duplicates skipped: {statuses['duplicate']}")
    print(f"  Rejected:           {statuses['rejected']}")
    for reason, count in rejected_reasons.items():
        print(f"    {reason}: {count}")
    print(f"  Gaps detected:      {gap_events} ({missed_total} missed packets)")
    print(f"  Values nulled as implausible: {dict(nulled_fields) or 'none'}")


if __name__ == "__main__":
    main()
