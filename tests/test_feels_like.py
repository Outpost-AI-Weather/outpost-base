import pytest

from outpost_base.stats.feels_like import (
    feels_like,
    humidex_from_dew_point,
    wind_chill_c,
)


def test_wind_chill_known_value():
    assert wind_chill_c(-10, 20) == pytest.approx(-17.9, abs=0.1)


def test_wind_chill_not_used_when_warm_or_calm():
    assert wind_chill_c(15, 20) is None
    assert wind_chill_c(-10, 0) is None


def test_wind_chill_light_wind_formula():
    assert round(wind_chill_c(-12, 3)) == -14


def test_humidex_published_examples():
    assert round(humidex_from_dew_point(30, 15)) == 34
    assert round(humidex_from_dew_point(30, 25)) == 42


def test_feels_like_picks_the_right_index():
    assert feels_like(-10, 60, 20)[1] == "wind_chill"
    assert feels_like(30, 70, 5)[1] == "humidex"
    assert feels_like(15, 50, 10)[1] == "air_temperature"
    assert feels_like(None, 50, 10) == (None, "unavailable")
