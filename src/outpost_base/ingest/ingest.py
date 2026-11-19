from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlmodel import Session, select

from outpost_base.db.models import Node, Reading

SUPPORTED_PROTOCOL_VERSIONS = {1}
SEQUENCE_MODULO = 65536

REQUIRED_FIELDS = ["protocol_version", "node_id", "sequence", "received_at"]

# Readings outside these ranges are treated as sensor glitches and stored as null
PLAUSIBLE_RANGES = {
    "temperature_c": (-50.0, 50.0),
    "humidity_pct": (0.0, 100.0),
    "pressure_pa": (80_000, 110_000),
    "wind_speed_ms": (0.0, 60.0),
    "wind_direction_deg": (0.0, 360.0),
}

# The fault name recorded when a field's value is rejected
FIELD_FAULTS = {
    "temperature_c": "temperature",
    "humidity_pct": "humidity",
    "pressure_pa": "pressure",
    "wind_speed_ms": "wind_speed",
    "wind_direction_deg": "wind_direction",
}


@dataclass
class IngestResult:
    status: str  # "saved", "duplicate", or "rejected"
    reason: str | None = None
    missed_packets: int = 0
    nulled_fields: list[str] = field(default_factory=list)


def parse_utc(timestamp: str) -> datetime:
    return datetime.fromisoformat(timestamp).astimezone(UTC)


def ingest_reading(session: Session, data: dict) -> IngestResult:
    """Check, clean, and save one decoder-format reading."""

    # Basic checks
    missing = [name for name in REQUIRED_FIELDS if data.get(name) is None]
    if missing:
        return IngestResult("rejected", reason=f"missing fields: {', '.join(missing)}")
    if data["protocol_version"] not in SUPPORTED_PROTOCOL_VERSIONS:
        return IngestResult(
            "rejected", reason=f"unknown protocol version {data['protocol_version']}"
        )

    received_at = parse_utc(data["received_at"])
    faults = list(data.get("faults") or [])

    # Pick measurement time
    node_timestamp = data.get("node_timestamp")
    if node_timestamp is not None and "clock_not_synced" not in faults:
        measured_at = datetime.fromtimestamp(node_timestamp, tz=UTC)
    else:
        measured_at = received_at

    # Skip duplicates
    duplicate = session.exec(
        select(Reading).where(
            Reading.node_id == data["node_id"],
            Reading.sequence == data["sequence"],
            Reading.measured_at == measured_at,
        )
    ).first()
    if duplicate:
        return IngestResult("duplicate")

    # Null out implausible values
    values = {}
    nulled = []
    for name, (low, high) in PLAUSIBLE_RANGES.items():
        value = data.get(name)
        if value is not None and not (low <= value <= high):
            value = None
            nulled.append(name)
            if FIELD_FAULTS[name] not in faults:
                faults.append(FIELD_FAULTS[name])
        values[name] = value

    # Find or create the node, and detect lost packets
    node = session.get(Node, data["node_id"])
    if node is None:
        node = Node(node_id=data["node_id"], name=f"Node {data['node_id']}")
        session.add(node)

    missed = 0
    if node.last_sequence is not None:
        missed = (data["sequence"] - node.last_sequence - 1) % SEQUENCE_MODULO

    # Save the reading and update the node
    raw_hex = data.get("raw_payload_hex")
    session.add(
        Reading(
            node_id=data["node_id"],
            sequence=data["sequence"],
            node_timestamp=node_timestamp,
            received_at=received_at,
            measured_at=measured_at,
            **values,
            battery_mv=data.get("battery_mv"),
            status_flags=data.get("status_flags", 0),
            faults=faults,
            rssi_dbm=data.get("rssi_dbm"),
            snr_db=data.get("snr_db"),
            protocol_version=data["protocol_version"],
            raw_payload=bytes.fromhex(raw_hex) if raw_hex else None,
        )
    )

    node.last_sequence = data["sequence"]
    node.last_packet_at = received_at
    node.last_status_flags = data.get("status_flags", 0)
    node.protocol_version = data["protocol_version"]

    session.commit()
    return IngestResult("saved", missed_packets=missed, nulled_fields=nulled)
