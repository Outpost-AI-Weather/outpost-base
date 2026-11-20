"""Longer-term stats: 7-day trends, yesterday's range, pressure tendency, data quality."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from outpost_base.stats.engine import (
    DEAD_BANDS,
    DISPLAY_DIGITS,
    SAME_TIME_TOLERANCE,
    change_direction,
    reading_near,
    rounded,
    value_or_none,
)

LOCAL_TIMEZONE = ZoneInfo("America/Toronto")
TREND_DAYS = 7

# Hourly mock data; set from the real sampling interval later
EXPECTED_INTERVAL = timedelta(hours=1)

# Change in the daily average per day needed to call a trend rising or falling
TREND_THRESHOLDS = {
    "temperature_c": 0.5,
    "humidity_pct": 2.0,
    "pressure_hpa": 1.0,
    "wind_speed_kmh": 1.0,
}

PRESSURE_TENDENCY_WINDOW = timedelta(hours=3)
RAPID_PRESSURE_DROP_HPA = 2.0

SENSOR_NAMES = {
    "temperature_c": "temperature",
    "humidity_pct": "humidity",
    "pressure_hpa": "pressure",
    "wind_speed_kmh": "wind_speed",
}


def seven_day_trend(df: pd.DataFrame, now: datetime) -> dict:
    """Average and direction of each measurement over the 7 complete days before today."""
    local = df.tz_convert(LOCAL_TIMEZONE)
    today = now.astimezone(LOCAL_TIMEZONE).date()
    first_day = today - timedelta(days=TREND_DAYS)
    window = local[(local.index.date >= first_day) & (local.index.date < today)]
    daily = window.resample("D").mean()

    quantities = {}
    for name, threshold in TREND_THRESHOLDS.items():
        values = daily[name].dropna()
        direction = None
        if len(values) >= 2:
            days = (values.index - values.index[0]).days
            slope = np.polyfit(days, values.to_numpy(), 1)[0]
            if abs(slope) < threshold:
                direction = "steady"
            else:
                direction = "rising" if slope > 0 else "falling"
        quantities[name] = {
            "mean": rounded(window[name].mean(), DISPLAY_DIGITS[name]),
            "direction": direction,
        }

    days_with_data = daily.dropna(how="all").index
    period = (
        f"{days_with_data[0].date().isoformat()} to {days_with_data[-1].date().isoformat()}"
        if len(days_with_data)
        else None
    )

    return {
        "period": period,
        "days_available": len(days_with_data),
        "quantities": quantities,
    }


def yesterday_temperature_range(df: pd.DataFrame, now: datetime) -> dict | None:
    """High and low temperature for the previous local calendar day."""
    local = df.tz_convert(LOCAL_TIMEZONE)
    yesterday = now.astimezone(LOCAL_TIMEZONE).date() - timedelta(days=1)
    temperatures = local[local.index.date == yesterday]["temperature_c"].dropna()
    if temperatures.empty:
        return None
    return {
        "date": yesterday.isoformat(),
        "high_c": rounded(temperatures.max(), 1),
        "low_c": rounded(temperatures.min(), 1),
    }


def pressure_tendency(df: pd.DataFrame, now: datetime) -> dict | None:
    """Pressure change over the last 3 hours."""
    current = reading_near(df, now, timedelta(0))
    earlier = reading_near(df, now - PRESSURE_TENDENCY_WINDOW, SAME_TIME_TOLERANCE)
    if current is None or earlier is None:
        return None

    now_value = value_or_none(current[0]["pressure_hpa"])
    then_value = value_or_none(earlier[0]["pressure_hpa"])
    if now_value is None or then_value is None:
        return None

    difference = now_value - then_value
    return {
        "change_hpa": rounded(abs(difference), 1),
        "direction": change_direction(difference, DEAD_BANDS["pressure_hpa"]),
        "rapid_drop": bool(difference <= -RAPID_PRESSURE_DROP_HPA),
    }


def data_quality(df: pd.DataFrame, now: datetime) -> dict:
    """How complete the last 24 hours of data is, and which sensors are missing now."""
    last_day = df[(df.index > now - timedelta(days=1)) & (df.index <= now)]
    expected = timedelta(days=1) / EXPECTED_INTERVAL
    completeness = min(100, round(100 * len(last_day) / expected))

    missing = []
    latest = reading_near(df, now, timedelta(0))
    if latest is not None:
        missing = [
            sensor
            for column, sensor in SENSOR_NAMES.items()
            if value_or_none(latest[0][column]) is None
        ]

    return {"completeness_pct_24h": completeness, "missing_sensors": missing}
