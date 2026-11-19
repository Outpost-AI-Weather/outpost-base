import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from outpost_base.db.models import Node, Reading
from outpost_base.ingest.ingest import ingest_reading


@pytest.fixture
def session():
    engine = create_engine("sqlite://")  # fresh in-memory database per test
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def make_reading(**overrides):
    """A valid decoder-format reading, with any fields overridden."""
    reading = {
        "protocol_version": 1,
        "node_id": 1,
        "sequence": 0,
        "node_timestamp": 1767243600,  # 2026-01-01 05:00 UTC
        "received_at": "2026-01-01T05:00:00Z",
        "temperature_c": -10.1,
        "humidity_pct": 59.0,
        "pressure_pa": 98170,
        "wind_speed_ms": 7.5,
        "wind_direction_deg": 320.0,
        "battery_mv": 12500,
        "status_flags": 0,
        "faults": [],
        "rssi_dbm": None,
        "snr_db": None,
        "raw_payload_hex": None,
    }
    reading.update(overrides)
    return reading


def test_saves_valid_reading(session):
    result = ingest_reading(session, make_reading())
    assert result.status == "saved"
    reading = session.exec(select(Reading)).one()
    assert reading.temperature_c == -10.1
    assert session.get(Node, 1).last_sequence == 0


def test_skips_duplicate(session):
    ingest_reading(session, make_reading())
    result = ingest_reading(session, make_reading())
    assert result.status == "duplicate"
    assert len(session.exec(select(Reading)).all()) == 1


def test_nulls_implausible_value(session):
    result = ingest_reading(session, make_reading(temperature_c=85.0))
    assert result.nulled_fields == ["temperature_c"]
    reading = session.exec(select(Reading)).one()
    assert reading.temperature_c is None
    assert "temperature" in reading.faults


def test_detects_lost_packets(session):
    ingest_reading(session, make_reading(sequence=0))
    result = ingest_reading(
        session,
        make_reading(
            sequence=3,
            node_timestamp=1767254400,
            received_at="2026-01-01T08:00:00Z",
        ),
    )
    assert result.missed_packets == 2


def test_sequence_wraparound_is_not_a_gap(session):
    ingest_reading(session, make_reading(sequence=65535))
    result = ingest_reading(
        session,
        make_reading(
            sequence=0,
            node_timestamp=1767247200,
            received_at="2026-01-01T06:00:00Z",
        ),
    )
    assert result.missed_packets == 0


def test_rejects_unknown_protocol(session):
    result = ingest_reading(session, make_reading(protocol_version=99))
    assert result.status == "rejected"
    assert session.exec(select(Reading)).all() == []


def test_uses_arrival_time_when_clock_not_synced(session):
    ingest_reading(
        session,
        make_reading(
            node_timestamp=0,
            faults=["clock_not_synced"],
            received_at="2026-01-01T05:00:00Z",
        ),
    )
    reading = session.exec(select(Reading)).one()
    assert reading.measured_at.year == 2026
    