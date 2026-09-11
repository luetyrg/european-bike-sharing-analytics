from __future__ import annotations

import pandas as pd


def safe_divide(numerator: float, denominator: float) -> float | None:
    if pd.isna(denominator) or denominator <= 0:
        return None
    return float(numerator) / float(denominator)


def trips_per_active_day(total_trips: int, active_days: int) -> float | None:
    return safe_divide(total_trips, active_days)


def fleet_utilization_proxy(
    total_trips: int, unique_bikes: int, active_days: int
) -> float | None:
    if unique_bikes <= 0 or active_days <= 0:
        return None
    return float(total_trips) / float(unique_bikes * active_days)


def valid_duration_seconds(duration: float | int | None) -> bool:
    if duration is None or pd.isna(duration):
        return False
    return 60 <= float(duration) <= 6 * 60 * 60


def filter_city_ids(frame: pd.DataFrame, city_ids: set[int]) -> pd.DataFrame:
    if "city_id" not in frame.columns:
        raise KeyError("city_id column is required")
    return frame.loc[frame["city_id"].isin(city_ids)].copy()
