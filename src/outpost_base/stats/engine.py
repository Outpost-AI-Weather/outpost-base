"""Stats engine: turns stored readings into the numbers the AI report uses."""

import math
from datetime import datetime, timedelta

import pandas as pd
from sqlmodel import Session, select

from outpost_base.db.models import Reading
from outpost_base.stats.feels_like import feels_like

# Hourly mock data; tighten once the real sampling interval is set
FRESHNESS_LIMIT = timedelta(minutes=90)

COMPASS_POINTS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
NUMERIC_COLUMNS = [
    "temperature_c",
    "humidity_pct",
    "pressure_hpa",
    "wind_speed_kmh",
    "wind_direction_deg",
]


def value_or_none(value):
    """Turn pandas' NaN into None."""
    return None if value is None or (isinstance(value, float) and math.isnan(value)) else value


def rounded(value, digits):
    """Round for display, keeping None. Zero digits gives a whole number."""
    value = value_or_none(value)
    if value is None:
        return None
    return round(value) if digits == 0 else round(value, digits)


def compass(degrees):
    degrees = value_or_none(degrees)
    if degrees is None:
        return None
    return COMPASS_POINTS[round(degrees / 45) % 8]


def load_readings(session: Session, node_id: int, start: datetime, end: datetime) -> pd.DataFrame:
    """Readings between start and end, in display units, indexed by measurement time."""
    rows = session.exec(
        select(Reading)
        .where(
            Reading.node_id == node_id,
            Reading.measured_at >= start,
            Reading.measured_at <= end,
        )
        .order_by(Reading.measured_at)
    ).all()

    df = pd.DataFrame(
        [
            {
                "measured_at": r.measured_at,
                "temperature_c": r.temperature_c,
                "humidity_pct": r.humidity_pct,
                "pressure_hpa": r.pressure_pa / 100 if r.pressure_pa is not None else None,
                "wind_speed_kmh": r.wind_speed_ms * 3.6 if r.wind_speed_ms is not None else None,
                "wind_direction_deg": r.wind_direction_deg,
            }
            for r in rows
        ],
        columns=["measured_at", *NUMERIC_COLUMNS],
    )
    df[NUMERIC_COLUMNS] = df[NUMERIC_COLUMNS].astype(float)
    df["measured_at"] = pd.to_datetime(df["measured_at"], utc=True)
    return df.set_index("measured_at")


def current_conditions(df: pd.DataFrame, at: datetime) -> dict | None:
    """The latest reading at or before `at`, or None if it's too old."""
    past = df[df.index <= at]
    if past.empty or at - past.index[-1] > FRESHNESS_LIMIT:
        return None

    latest = past.iloc[-1]
    temperature = value_or_none(latest["temperature_c"])
    humidity = value_or_none(latest["humidity_pct"])
    wind = value_or_none(latest["wind_speed_kmh"])
    feels, feels_type = feels_like(temperature, humidity, wind)

    return {
        "measured_at": past.index[-1].isoformat(),
        "temperature_c": rounded(temperature, 1),
        "humidity_pct": rounded(humidity, 0),
        "pressure_hpa": rounded(latest["pressure_hpa"], 1),
        "wind_speed_kmh": rounded(wind, 0),
        "wind_direction": compass(latest["wind_direction_deg"]),
        "feels_like_c": rounded(feels, 0),
        "feels_like_type": feels_type,
    }