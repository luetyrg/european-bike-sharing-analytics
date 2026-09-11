"""Download, profile, select, and prepare the analytical trip subset."""

from __future__ import annotations

import shutil
import urllib.request
import zipfile
from pathlib import Path

import duckdb
import pandas as pd

from src.config import (
    ALTERNATE_CITIES,
    ARCHIVE_PATH,
    CANDIDATE_CITY_GROUPS,
    DATASET_URL,
    FULL_RAW_DIR,
    INTERIM_DIR,
    MAX_DISTANCE_METERS,
    MAX_DURATION_SECONDS,
    MAX_SPEED_KMH,
    MIN_DURATION_SECONDS,
    MIN_SELECTION_ACTIVE_DAYS,
    MIN_SELECTION_TRIPS,
    MIN_VALID_DURATION_SHARE,
    PREFERRED_CITIES,
    PROCESSED_DIR,
    SOURCE_TABLES,
    ensure_directories,
)

TRIP_COLUMNS = {
    "bike_id": "BIGINT",
    "city_id": "BIGINT",
    "time_start": "DOUBLE",
    "lon_start": "DOUBLE",
    "lat_start": "DOUBLE",
    "lon_end": "DOUBLE",
    "lat_end": "DOUBLE",
    "station_id_start": "BIGINT",
    "station_id_end": "BIGINT",
    "battery_start": "DOUBLE",
    "battery_end": "DOUBLE",
    "duration": "DOUBLE",
    "distance": "DOUBLE",
}

EXPECTED_COLUMNS = {
    "trips.csv": set(TRIP_COLUMNS),
    "cities.csv": {
        "id",
        "name",
        "lat",
        "lon",
        "timezone",
        "country",
        "return_to_official_only",
    },
    "stations.csv": {"id", "city_id", "name", "lon", "lat"},
    "bikes.csv": {"id", "bike_type_id"},
    "bike_types.csv": {"id", "name", "form_factor", "propulsion_type"},
}


def _sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def _columns_sql(columns: dict[str, str]) -> str:
    return "{" + ", ".join(f"'{name}': '{dtype}'" for name, dtype in columns.items()) + "}"


def download_archive(destination: Path = ARCHIVE_PATH) -> Path:
    """Download the official archive once, with a temporary partial file."""

    ensure_directories()
    if destination.exists() and destination.stat().st_size > 100_000_000:
        return destination
    partial = destination.with_suffix(".zip.part")
    with urllib.request.urlopen(DATASET_URL) as response, partial.open("wb") as output:
        shutil.copyfileobj(response, output, length=8 * 1024 * 1024)
    partial.replace(destination)
    return destination


def extract_source_tables(archive: Path = ARCHIVE_PATH) -> Path:
    """Extract only tables used by the project, excluding station snapshots."""

    ensure_directories()
    with zipfile.ZipFile(archive) as bundle:
        names = {Path(name).name: name for name in bundle.namelist()}
        for table in SOURCE_TABLES:
            target = FULL_RAW_DIR / table
            if target.exists() and target.stat().st_size > 0:
                continue
            if table not in names:
                raise FileNotFoundError(f"{table} is missing from {archive}")
            with bundle.open(names[table]) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output, length=8 * 1024 * 1024)
    return FULL_RAW_DIR


def validate_source_schema(source_dir: Path) -> None:
    """Fail early when the official schema no longer matches the pipeline."""

    for filename, required in EXPECTED_COLUMNS.items():
        path = source_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Required source table is missing: {path}")
        actual = set(pd.read_csv(path, nrows=0).columns)
        missing = required - actual
        if missing:
            raise ValueError(f"{filename} is missing columns: {sorted(missing)}")


def build_city_map(cities: pd.DataFrame) -> pd.DataFrame:
    """Resolve candidate groups from canonical names in the source dimension."""

    records: list[dict[str, object]] = []
    for display_city, source_names in CANDIDATE_CITY_GROUPS.items():
        matches = cities.loc[cities["name"].isin(source_names)]
        if matches.empty:
            raise ValueError(f"No canonical city row found for {display_city}: {source_names}")
        for row in matches.itertuples(index=False):
            records.append(
                {
                    "city": display_city,
                    "city_id": int(row.id),
                    "source_city_name": str(row.name),
                    "timezone": str(row.timezone),
                    "country": str(row.country),
                }
            )
    return pd.DataFrame(records)


def materialize_candidate_trips(source_dir: Path, force: bool = False) -> Path:
    """Scan the full trips CSV once and save only candidate city rows."""

    ensure_directories()
    output = INTERIM_DIR / "candidate_trips.parquet"
    if output.exists() and not force:
        return output
    cities = pd.read_csv(source_dir / "cities.csv")
    city_map = build_city_map(cities)
    ids = ", ".join(str(value) for value in sorted(city_map["city_id"].unique()))
    connection = duckdb.connect()
    try:
        connection.execute(
            f"""
            COPY (
                SELECT *
                FROM read_csv(
                    '{_sql_path(source_dir / 'trips.csv')}',
                    header = true,
                    columns = {_columns_sql(TRIP_COLUMNS)},
                    nullstr = ''
                )
                WHERE city_id IN ({ids})
            ) TO '{_sql_path(output)}'
            (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 100000)
            """
        )
    finally:
        connection.close()
    return output


def profile_candidates(source_dir: Path, candidate_path: Path) -> pd.DataFrame:
    """Profile volume, coverage, key-field quality, stations, and bike types."""

    cities = pd.read_csv(source_dir / "cities.csv")
    stations = pd.read_csv(source_dir / "stations.csv", low_memory=False)
    bikes = pd.read_csv(source_dir / "bikes.csv")
    bike_types = pd.read_csv(source_dir / "bike_types.csv")
    city_map = build_city_map(cities)

    connection = duckdb.connect()
    connection.register("city_map", city_map)
    connection.register("stations_dim", stations)
    connection.register("bikes_dim", bikes)
    connection.register("bike_types_dim", bike_types)
    try:
        profile = connection.execute(
            f"""
            WITH raw AS (
                SELECT
                    cm.city,
                    cm.source_city_name,
                    cm.timezone,
                    t.*,
                    timezone(cm.timezone, to_timestamp(t.time_start)) AS local_start,
                    CASE WHEN t.duration BETWEEN {MIN_DURATION_SECONDS}
                              AND {MAX_DURATION_SECONDS} THEN 1 ELSE 0 END AS valid_duration,
                    CASE WHEN t.distance > 0 AND t.distance <= {MAX_DISTANCE_METERS}
                              AND (t.duration IS NULL OR t.duration <= 0
                                   OR t.distance / t.duration * 3.6 <= {MAX_SPEED_KMH})
                         THEN 1 ELSE 0 END AS valid_distance
                FROM read_parquet('{_sql_path(candidate_path)}') t
                INNER JOIN city_map cm USING (city_id)
            ),
            station_counts AS (
                SELECT cm.city, COUNT(DISTINCT s.id) AS stations
                FROM stations_dim s
                INNER JOIN city_map cm ON s.city_id = cm.city_id
                GROUP BY cm.city
            ),
            type_counts AS (
                SELECT
                    r.city,
                    COUNT(DISTINCT CASE WHEN bt.propulsion_type IS NOT NULL
                                        THEN bt.propulsion_type END) AS bike_type_categories,
                    COUNT(*) FILTER (WHERE bt.propulsion_type IS NOT NULL) AS typed_trips
                FROM raw r
                LEFT JOIN bikes_dim b ON r.bike_id = b.id
                LEFT JOIN bike_types_dim bt ON b.bike_type_id = bt.id
                GROUP BY r.city
            )
            SELECT
                r.city,
                string_agg(DISTINCT r.source_city_name, ', ' ORDER BY r.source_city_name)
                    AS source_city_names,
                string_agg(DISTINCT CAST(r.city_id AS VARCHAR), ', '
                    ORDER BY CAST(r.city_id AS VARCHAR)) AS source_city_ids,
                COUNT(*) AS total_trips,
                MIN(CAST(r.local_start AS DATE)) AS observation_start,
                MAX(CAST(r.local_start AS DATE)) AS observation_end,
                COUNT(DISTINCT CAST(r.local_start AS DATE)) AS active_days,
                COALESCE(sc.stations, 0) AS stations,
                COUNT(DISTINCT r.bike_id) AS unique_bikes,
                AVG((r.bike_id IS NULL)::INT) AS missing_bike_share,
                AVG((r.station_id_start IS NULL)::INT) AS missing_start_station_share,
                AVG((r.station_id_end IS NULL)::INT) AS missing_end_station_share,
                AVG(r.valid_duration) AS valid_duration_share,
                AVG(r.valid_distance) AS valid_distance_share,
                AVG((r.time_start IS NULL)::INT) AS missing_timestamp_share,
                tc.bike_type_categories,
                tc.typed_trips / COUNT(*)::DOUBLE AS typed_trip_share
            FROM raw r
            LEFT JOIN station_counts sc USING (city)
            LEFT JOIN type_counts tc USING (city)
            GROUP BY r.city, sc.stations, tc.bike_type_categories, tc.typed_trips
            ORDER BY total_trips DESC
            """
        ).fetchdf()
    finally:
        connection.close()
    return profile


def select_cities(profile: pd.DataFrame) -> pd.DataFrame:
    """Retain preferred cities unless their data fails explicit minimums."""

    indexed = profile.set_index("city")

    def eligible(city: str) -> bool:
        if city not in indexed.index:
            return False
        row = indexed.loc[city]
        return bool(
            row["total_trips"] >= MIN_SELECTION_TRIPS
            and row["active_days"] >= MIN_SELECTION_ACTIVE_DAYS
            and row["valid_duration_share"] >= MIN_VALID_DURATION_SHARE
        )

    selected: list[dict[str, str]] = []
    available_alternates = [city for city in ALTERNATE_CITIES if eligible(city)]
    available_alternates.sort(
        key=lambda city: (indexed.loc[city, "active_days"], indexed.loc[city, "total_trips"]),
        reverse=True,
    )
    for city in PREFERRED_CITIES:
        if eligible(city):
            selected.append({"city": city, "selection_reason": "Preferred city; quality thresholds passed"})
            continue
        if city in {"Berlin", "Bilbao"}:
            raise ValueError(f"Required city {city} is not technically suitable; inspect profile")
        if not available_alternates:
            raise ValueError(f"No suitable alternate is available for {city}")
        replacement = available_alternates.pop(0)
        selected.append(
            {
                "city": replacement,
                "selection_reason": (
                    f"Replacement for {city}; preferred city failed volume, coverage, "
                    "or duration-quality thresholds"
                ),
            }
        )
    result = pd.DataFrame(selected).drop_duplicates("city")
    if len(result) != 4:
        raise ValueError("City selection did not produce four distinct cities")
    return result


def prepare_selected_trips(
    source_dir: Path,
    candidate_path: Path,
    selected: pd.DataFrame,
) -> tuple[Path, pd.DataFrame]:
    """Deduplicate, join dimensions, localize time, and apply quality flags."""

    ensure_directories()
    output = INTERIM_DIR / "trips_selected.parquet"
    cities = pd.read_csv(source_dir / "cities.csv")
    city_map = build_city_map(cities)
    city_map = city_map.loc[city_map["city"].isin(selected["city"])]
    stations = pd.read_csv(source_dir / "stations.csv", low_memory=False)
    bikes = pd.read_csv(source_dir / "bikes.csv")
    bike_types = pd.read_csv(source_dir / "bike_types.csv")

    connection = duckdb.connect()
    connection.register("city_map", city_map)
    connection.register("stations_dim", stations)
    connection.register("bikes_dim", bikes)
    connection.register("bike_types_dim", bike_types)
    try:
        connection.execute(
            f"""
            COPY (
                WITH selected_raw AS (
                    SELECT t.*, cm.city, cm.source_city_name, cm.timezone
                    FROM read_parquet('{_sql_path(candidate_path)}') t
                    INNER JOIN city_map cm USING (city_id)
                ),
                deduplicated AS (
                    SELECT DISTINCT * FROM selected_raw
                ),
                prepared AS (
                    SELECT
                        d.city,
                        d.city_id AS source_city_id,
                        d.source_city_name,
                        d.bike_id,
                        timezone(d.timezone, to_timestamp(d.time_start)) AS trip_start_local,
                        CAST(timezone(d.timezone, to_timestamp(d.time_start)) AS DATE) AS trip_date,
                        EXTRACT('hour' FROM timezone(d.timezone, to_timestamp(d.time_start)))::INTEGER
                            AS hour,
                        ((EXTRACT('isodow' FROM timezone(d.timezone, to_timestamp(d.time_start)))
                            - 1)::INTEGER) AS day_of_week,
                        strftime(timezone(d.timezone, to_timestamp(d.time_start)), '%A') AS day_name,
                        EXTRACT('isodow' FROM timezone(d.timezone, to_timestamp(d.time_start)))
                            IN (6, 7) AS is_weekend,
                        d.station_id_start AS start_station_id,
                        ss.name AS start_station_name,
                        d.station_id_end AS end_station_id,
                        se.name AS end_station_name,
                        d.lon_start,
                        d.lat_start,
                        d.lon_end,
                        d.lat_end,
                        CASE WHEN d.duration BETWEEN {MIN_DURATION_SECONDS}
                                  AND {MAX_DURATION_SECONDS}
                             THEN d.duration / 60.0 END AS duration_min,
                        CASE WHEN d.distance > 0 AND d.distance <= {MAX_DISTANCE_METERS}
                                  AND (d.duration IS NULL OR d.duration <= 0
                                       OR d.distance / d.duration * 3.6 <= {MAX_SPEED_KMH})
                             THEN d.distance / 1000.0 END AS distance_km,
                        COALESCE(bt.name, 'Unknown') AS bike_type_name,
                        COALESCE(bt.propulsion_type, 'unknown') AS propulsion_type,
                        d.battery_start,
                        d.battery_end,
                        d.station_id_start IS NOT NULL AND d.station_id_end IS NOT NULL
                            AS has_station_pair
                    FROM deduplicated d
                    LEFT JOIN stations_dim ss ON d.station_id_start = ss.id
                    LEFT JOIN stations_dim se ON d.station_id_end = se.id
                    LEFT JOIN bikes_dim b ON d.bike_id = b.id
                    LEFT JOIN bike_types_dim bt ON b.bike_type_id = bt.id
                    WHERE d.time_start IS NOT NULL
                      AND to_timestamp(d.time_start) >= TIMESTAMPTZ '2010-01-01 00:00:00+00'
                      AND to_timestamp(d.time_start) < TIMESTAMPTZ '2030-01-01 00:00:00+00'
                )
                SELECT * FROM prepared
            ) TO '{_sql_path(output)}'
            (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 100000)
            """
        )

        quality = connection.execute(
            f"""
            WITH selected_raw AS (
                SELECT t.*, cm.city
                FROM read_parquet('{_sql_path(candidate_path)}') t
                INNER JOIN city_map cm USING (city_id)
            ),
            distinct_raw AS (SELECT DISTINCT * FROM selected_raw),
            source_counts AS (
                SELECT
                    city,
                    COUNT(*) AS source_rows,
                    COUNT(*) - COUNT(DISTINCT hash(
                        bike_id, city_id, time_start, lon_start, lat_start, lon_end, lat_end,
                        station_id_start, station_id_end, battery_start, battery_end, duration, distance
                    )) AS duplicate_rows,
                    COUNT(*) FILTER (
                        WHERE time_start IS NULL
                           OR to_timestamp(time_start) < TIMESTAMPTZ '2010-01-01 00:00:00+00'
                           OR to_timestamp(time_start) >= TIMESTAMPTZ '2030-01-01 00:00:00+00'
                    ) AS invalid_timestamp_rows,
                    COUNT(*) FILTER (
                        WHERE duration IS NULL OR duration < {MIN_DURATION_SECONDS}
                           OR duration > {MAX_DURATION_SECONDS}
                    ) AS invalid_duration_rows,
                    COUNT(*) FILTER (
                        WHERE distance IS NULL OR distance <= 0 OR distance > {MAX_DISTANCE_METERS}
                           OR (duration > 0 AND distance / duration * 3.6 > {MAX_SPEED_KMH})
                    ) AS invalid_distance_rows,
                    COUNT(*) FILTER (WHERE station_id_start IS NULL) AS missing_start_station_rows,
                    COUNT(*) FILTER (WHERE station_id_end IS NULL) AS missing_end_station_rows,
                    COUNT(*) FILTER (WHERE bike_id IS NULL) AS missing_bike_rows
                FROM selected_raw
                GROUP BY city
            ),
            retained AS (
                SELECT city, COUNT(*) AS retained_rows
                FROM read_parquet('{_sql_path(output)}')
                GROUP BY city
            )
            SELECT s.*, r.retained_rows
            FROM source_counts s
            JOIN retained r USING (city)
            ORDER BY s.city
            """
        ).fetchdf()
    finally:
        connection.close()
    return output, quality


def save_preparation_outputs(
    profile: pd.DataFrame, selected: pd.DataFrame, quality: pd.DataFrame
) -> None:
    """Persist compact evidence used by the analysis and documentation."""

    ensure_directories()
    profile.to_parquet(PROCESSED_DIR / "city_profile.parquet", index=False)
    selected.to_parquet(PROCESSED_DIR / "selected_cities.parquet", index=False)
    quality.to_parquet(PROCESSED_DIR / "data_quality.parquet", index=False)
