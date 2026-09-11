"""Small, testable metric helpers used by the analysis and dashboard."""

from __future__ import annotations

import pandas as pd


def safe_divide(numerator: float, denominator: float) -> float | None:
    """Return a ratio, or None when the denominator is missing or non-positive."""

    if pd.isna(denominator) or denominator <= 0:
        return None
    return float(numerator) / float(denominator)


def trips_per_active_day(total_trips: int, active_days: int) -> float | None:
    """Normalize observed demand for unequal time coverage."""

    return safe_divide(total_trips, active_days)


def fleet_utilization_proxy(
    total_trips: int, unique_bikes: int, active_days: int
) -> float | None:
    """Trips per observed unique bike per active day.

    This is a utilization proxy because the source contains bikes observed in
    trips, not a guaranteed complete fleet registry for every service period.
    """

    if unique_bikes <= 0 or active_days <= 0:
        return None
    return float(total_trips) / float(unique_bikes * active_days)


def valid_duration_seconds(duration: float | int | None) -> bool:
    """Apply the documented duration rule used during preparation."""

    if duration is None or pd.isna(duration):
        return False
    return 60 <= float(duration) <= 6 * 60 * 60


def filter_city_ids(frame: pd.DataFrame, city_ids: set[int]) -> pd.DataFrame:
    """Return trips belonging to the requested upstream city IDs."""

    if "city_id" not in frame.columns:
        raise KeyError("city_id column is required")
    return frame.loc[frame["city_id"].isin(city_ids)].copy()

