from datetime import UTC, datetime

from sqlmodel import Session, SQLModel, create_engine, select

from outpost_base.db.models import Node, Reading


def test_reading_round_trip():
    engine = create_engine("sqlite://")  # in-memory database
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(Node(node_id=1, name="Test node"))
        session.commit()

        session.add(
            Reading(
                node_id=1,
                sequence=5,
                received_at=datetime(2026, 1, 1, 5, 0, tzinfo=UTC),
                temperature_c=-10.1,
                humidity_pct=None,
                faults=["humidity"],
                protocol_version=1,
                raw_payload=bytes.fromhex("0101"),
            )
        )
        session.commit()

        reading = session.exec(select(Reading)).one()
        assert reading.temperature_c == -10.1
        assert reading.humidity_pct is None
        assert reading.faults == ["humidity"]
        assert reading.raw_payload == b"\x01\x01"
