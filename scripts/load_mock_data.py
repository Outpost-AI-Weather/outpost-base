"""Load decoder-format JSON Lines mock data into the database."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlmodel import Session, SQLModel

from outpost_base.db.models import Node, Reading
from outpost_base.db.session import create_db_and_tables, engine


def to_utc(timestamp: str) -> datetime:
    """Parse an ISO 8601 UTC time, keeping the UTC timezone."""
    return datetime.fromisoformat(timestamp).astimezone(UTC)


def to_reading(data: dict) -> Reading:
    raw_hex = data.get("raw_payload_hex")
    return Reading(
        node_id=data["node_id"],
        sequence=data["sequence"],
        node_timestamp=data["node_timestamp"],
        received_at=to_utc(data["received_at"]),        temperature_c=data["temperature_c"],
        humidity_pct=data["humidity_pct"],
        pressure_pa=data["pressure_pa"],
        wind_speed_ms=data["wind_speed_ms"],
        wind_direction_deg=data["wind_direction_deg"],
        battery_mv=data["battery_mv"],
        status_flags=data["status_flags"],
        faults=data["faults"],
        rssi_dbm=data["rssi_dbm"],
        snr_db=data["snr_db"],
        protocol_version=data["protocol_version"],
        raw_payload=bytes.fromhex(raw_hex) if raw_hex else None,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON Lines file of decoder-format readings")
    parser.add_argument("--reset", action="store_true", help="clear all tables first")
    args = parser.parse_args()

    if args.reset:
        SQLModel.metadata.drop_all(engine)
    create_db_and_tables()

    lines = Path(args.input).read_text().splitlines()
    readings = [to_reading(json.loads(line)) for line in lines if line.strip()]

    with Session(engine) as session:
        for node_id in {r.node_id for r in readings}:
            if session.get(Node, node_id) is None:
                session.add(Node(node_id=node_id, name=f"Node {node_id}"))
        session.commit()

        session.add_all(readings)

        latest = max(readings, key=lambda r: r.received_at)
        node = session.get(Node, latest.node_id)
        node.protocol_version = latest.protocol_version
        node.last_packet_at = latest.received_at
        node.last_status_flags = latest.status_flags

        session.commit()

    print(f"Loaded {len(readings)} readings from {args.input}")


if __name__ == "__main__":
    main()
