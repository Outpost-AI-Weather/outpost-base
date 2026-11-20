"""Builds the complete stats payload that the AI report is generated from."""

from datetime import datetime, timedelta

from sqlmodel import Session

from outpost_base.stats.engine import (
    compare_with_yesterday,
    current_conditions,
    load_readings,
)
from outpost_base.stats.trends import (
    LOCAL_TIMEZONE,
    TREND_DAYS,
    data_quality,
    pressure_tendency,
    seven_day_trend,
    yesterday_temperature_range,
)

SCHEMA_VERSION = "1.0"

# Enough history for the 7-day trend plus yesterday's comparison
LOOKBACK = timedelta(days=TREND_DAYS + 2)


def build_stats(session: Session, node_id: int, at: datetime) -> dict:
    """All stats for a report at time `at`. Every section is present; missing data is None."""
    window_start = at - LOOKBACK
    df = load_readings(session, node_id, window_start, at)
    current = current_conditions(df, at)

    stats = {
        "schema_version": SCHEMA_VERSION,
        "node_id": node_id,
        "report_time_local": at.astimezone(LOCAL_TIMEZONE).strftime("%Y-%m-%d %H:%M"),
        "window": {"start": window_start.isoformat(), "end": at.isoformat()},
        "station_online": current is not None,
        "current": current,
        "vs_yesterday": None,
        "yesterday_temperature_range": None,
        "trend_7_day": None,
        "pressure_change_3h": None,
        "data_quality": data_quality(df, at),
    }

    if current is None:
        return stats

    now = datetime.fromisoformat(current["measured_at"])
    stats["vs_yesterday"] = compare_with_yesterday(df, now)
    stats["yesterday_temperature_range"] = yesterday_temperature_range(df, now)
    stats["trend_7_day"] = seven_day_trend(df, now)
    stats["pressure_change_3h"] = pressure_tendency(df, now)
    stats["data_quality"] = data_quality(df, now)
    return stats
