"""Prepare the reusable trip-level Parquet subset from the official CSV export."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import FULL_RAW_DIR, SAMPLE_RAW_DIR, ensure_directories  # noqa: E402
from src.data import (  # noqa: E402
    build_city_map,
    download_archive,
    extract_source_tables,
    materialize_candidate_trips,
    prepare_selected_trips,
    profile_candidates,
    save_preparation_outputs,
    select_cities,
    validate_source_schema,
)


def sample_smoke_test() -> None:
    """Validate schema and one representative relational join on sample files."""

    validate_source_schema(SAMPLE_RAW_DIR)
    trips = pd.read_csv(SAMPLE_RAW_DIR / "trips.csv")
    cities = pd.read_csv(SAMPLE_RAW_DIR / "cities.csv")
    connection = duckdb.connect()
    connection.register("sample_trips", trips)
    connection.register("sample_cities", cities)
    try:
        result = connection.execute(
            """
            SELECT COUNT(*) AS trips, COUNT(DISTINCT c.id) AS matched_cities
            FROM sample_trips t
            INNER JOIN sample_cities c ON t.city_id = c.id
            """
        ).fetchone()
    finally:
        connection.close()
    print(f"Sample schema and JOIN passed: {result[0]:,} trips, {result[1]} cities")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Run the inexpensive schema/JOIN development check only.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild the candidate Parquet subset even when it already exists.",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Require source files to exist locally instead of downloading the archive.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_directories()
    if args.sample:
        sample_smoke_test()
        return

    if not all((FULL_RAW_DIR / name).exists() for name in ("trips.csv", "cities.csv")):
        if args.skip_download:
            raise FileNotFoundError("Full source files are absent and --skip-download was supplied")
        archive = download_archive()
        extract_source_tables(archive)

    validate_source_schema(FULL_RAW_DIR)
    cities = pd.read_csv(FULL_RAW_DIR / "cities.csv")
    city_map = build_city_map(cities)
    print("Candidate source IDs:")
    print(city_map.to_string(index=False))

    candidate_path = materialize_candidate_trips(FULL_RAW_DIR, force=args.force)
    profile = profile_candidates(FULL_RAW_DIR, candidate_path)
    selected = select_cities(profile)
    selected_path, quality = prepare_selected_trips(
        FULL_RAW_DIR, candidate_path, selected
    )
    save_preparation_outputs(profile, selected, quality)

    print("\nCandidate profile:")
    print(profile.to_string(index=False))
    print("\nSelected cities:")
    print(selected.to_string(index=False))
    print("\nData quality summary:")
    print(quality.to_string(index=False))
    print(f"\nPrepared subset: {selected_path}")
    row_count = duckdb.sql(
        f"SELECT COUNT(*) FROM read_parquet('{selected_path.as_posix()}')"
    ).fetchone()[0]
    print(f"Rows: {row_count:,}")


if __name__ == "__main__":
    main()
