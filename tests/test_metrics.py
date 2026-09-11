"""Tests for the small calculations most likely to distort comparisons."""

import pandas as pd
import pytest

from src.metrics import (
    filter_city_ids,
    fleet_utilization_proxy,
    trips_per_active_day,
    valid_duration_seconds,
)


def test_trips_per_active_day_uses_observed_days() -> None:
    assert trips_per_active_day(1_000, 20) == pytest.approx(50.0)
    assert trips_per_active_day(1_000, 0) is None


def test_fleet_utilization_proxy_uses_bikes_and_days() -> None:
    assert fleet_utilization_proxy(2_400, 20, 30) == pytest.approx(4.0)
    assert fleet_utilization_proxy(2_400, 0, 30) is None


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(None, False), (0, False), (59, False), (60, True), (21_600, True), (21_601, False)],
)
def test_duration_boundaries(seconds: int | None, expected: bool) -> None:
    assert valid_duration_seconds(seconds) is expected


def test_city_filter_returns_copy_for_selected_ids() -> None:
    source = pd.DataFrame({"city_id": [362, 532, 8], "trips": [1, 2, 3]})
    result = filter_city_ids(source, {362, 532})
    assert result["city_id"].tolist() == [362, 532]
    result.loc[:, "trips"] = 99
    assert source["trips"].tolist() == [1, 2, 3]

