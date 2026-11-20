from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, SQLModel, create_engine

from outpost_base.ingest.ingest import ingest_reading
from outpost_base.stats.builder import build_stats

START = datetime(2026, 1, 1, 5, tzinfo=UTC)  # midnight in Toronto
REPORT_TIME = START + timedelta(days=9, hours=7)  # 7:00 AM Toronto on January 10


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        for i in range(240):  # 10 days of hourly readings
            time = START + timedelta(hours=i)
            ingest_reading(
                session,
                {
                    "protocol_version": 1,
                    "node_id": 1,
                    "sequence": i,
                    "node_timestamp": int(time.timestamp()),
                    "received_at": time.isoformat(),
                    "temperature_c": round(-30 + i / 12, 2),  # rises 2°C per day
                    "humidity_pct": 60.0,
                    "pressure_pa": 100000,
                    "wind_speed_ms": 5.0,
                    "wind_direction_deg": 270.0,
                    "battery_mv": 12500,
                    "status_flags": 0,
                    "faults": [],
                },
            )
        yield session


def test_current_conditions(session):
    stats = build_stats(session, 1, REPORT_TIME)
    assert stats["station_online"] is True
    assert stats["report_time_local"] == "2026-01-10 07:00"
    current = stats["current"]
    assert current["temperature_c"] == -11.4
    assert current["pressure_hpa"] == 1000.0
    assert current["wind_speed_kmh"] == 18
    assert current["wind_direction"] == "W"
    assert current["feels_like_type"] == "wind_chill"


def test_compared_with_yesterday(session):
    temperature = build_stats(session, 1, REPORT_TIME)["vs_yesterday"]["quantities"][
        "temperature_c"
    ]
    assert temperature == {"previous": -13.4, "change": 2.0, "direction": "higher"}


def test_seven_day_trend(session):
    trend = build_stats(session, 1, REPORT_TIME)["trend_7_day"]
    assert trend["period"] == "2026-01-03 to 2026-01-09"
    assert trend["days_available"] == 7
    assert trend["quantities"]["temperature_c"]["direction"] == "rising"
    assert trend["quantities"]["humidity_pct"]["direction"] == "steady"
    assert trend["quantities"]["pressure_hpa"]["direction"] == "steady"


def test_yesterday_range_and_pressure(session):
    stats = build_stats(session, 1, REPORT_TIME)
    assert stats["yesterday_temperature_range"] == {
        "date": "2026-01-09",
        "high_c": -12.1,
        "low_c": -14.0,
    }
    assert stats["pressure_change_3h"]["rapid_drop"] is False


def test_data_quality(session):
    quality = build_stats(session, 1, REPORT_TIME)["data_quality"]
    assert quality == {"completeness_pct_24h": 100, "missing_sensors": []}


def test_offline_when_no_recent_data(session):
    stats = build_stats(session, 1, START + timedelta(days=20))
    assert stats["station_online"] is False
    assert stats["current"] is None
