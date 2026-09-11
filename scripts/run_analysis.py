"""Execute the DuckDB SQL analysis and build processed tables and figures."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import FIGURES_DIR, INTERIM_DIR, PROCESSED_DIR, SQL_DIR, ensure_directories  # noqa: E402
from src.visualization import create_all_figures  # noqa: E402


def result_name(sql_path: Path) -> str:
    """Drop the numeric ordering prefix from a SQL filename."""

    return sql_path.stem.split("_", maxsplit=1)[1]


def main() -> None:
    ensure_directories()
    trips_path = INTERIM_DIR / "trips_selected.parquet"
    profile_path = PROCESSED_DIR / "city_profile.parquet"
    if not trips_path.exists():
        raise FileNotFoundError("Run python scripts/prepare_data.py before analysis")

    connection = duckdb.connect()
    results = {}
    try:
        connection.execute(
            f"CREATE VIEW trips AS SELECT * FROM read_parquet('{trips_path.as_posix()}')"
        )
        connection.execute(
            f"CREATE VIEW city_profile AS SELECT * FROM read_parquet('{profile_path.as_posix()}')"
        )
        for sql_path in sorted(SQL_DIR.glob("*.sql")):
            name = result_name(sql_path)
            frame = connection.execute(sql_path.read_text(encoding="utf-8")).fetchdf()
            frame.to_parquet(PROCESSED_DIR / f"{name}.parquet", index=False)
            results[name] = frame
            print(f"{sql_path.name}: {len(frame):,} rows")

        overview = connection.execute(
            """
            SELECT
                COUNT(*) AS rows,
                MIN(trip_date) AS observation_start,
                MAX(trip_date) AS observation_end,
                COUNT(DISTINCT city) AS cities
            FROM trips
            """
        ).fetchone()
    finally:
        connection.close()

    figure_paths = create_all_figures(results, FIGURES_DIR)
    metadata = {
        "analytical_rows": int(overview[0]),
        "observation_start": str(overview[1]),
        "observation_end": str(overview[2]),
        "cities": int(overview[3]),
        "interim_parquet_bytes": trips_path.stat().st_size,
        "figures": [path.name for path in figure_paths],
    }
    (PROCESSED_DIR / "analysis_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    print(f"Created {len(figure_paths)} figures in {FIGURES_DIR}")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()

