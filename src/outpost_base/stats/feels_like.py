import math


def dew_point_c(temperature_c: float, humidity_pct: float) -> float:
    """Dew point from temperature and relative humidity (Magnus formula)."""
    a, b = 17.625, 243.04
    gamma = math.log(humidity_pct / 100) + a * temperature_c / (b + temperature_c)
    return b * gamma / (a - gamma)


def wind_chill_c(temperature_c: float, wind_kmh: float) -> float | None:
    """Wind chill using Environment Canada's formulas, or None when it doesn't apply."""
    if temperature_c > 10 or wind_kmh <= 0:
        return None
    if wind_kmh < 4.8:
        # Environment Canada's light-wind formula
        return temperature_c + ((-1.59 + 0.1345 * temperature_c) / 5) * wind_kmh
    v = wind_kmh**0.16
    return 13.12 + 0.6215 * temperature_c - 11.37 * v + 0.3965 * temperature_c * v


def humidex_from_dew_point(temperature_c: float, dew_point: float) -> float:
    """Humidex from temperature and dew point."""
    vapour_pressure = 6.11 * math.exp(5417.7530 * (1 / 273.16 - 1 / (273.15 + dew_point)))
    return temperature_c + 0.5555 * (vapour_pressure - 10)


def humidex_c(temperature_c: float, humidity_pct: float) -> float | None:
    """Humidex, or None when Environment Canada wouldn't report it."""
    if temperature_c < 20 or humidity_pct <= 0:
        return None
    value = humidex_from_dew_point(temperature_c, dew_point_c(temperature_c, humidity_pct))
    return value if value - temperature_c >= 1 else None


def feels_like(
    temperature_c: float | None, humidity_pct: float | None, wind_kmh: float | None
) -> tuple[float | None, str]:
    """Return (feels-like temperature, which index was used)."""
    if temperature_c is None:
        return None, "unavailable"
    if wind_kmh is not None:
        chill = wind_chill_c(temperature_c, wind_kmh)
        if chill is not None:
            return chill, "wind_chill"
    if humidity_pct is not None:
        hx = humidex_c(temperature_c, humidity_pct)
        if hx is not None:
            return hx, "humidex"
    return temperature_c, "air_temperature"
