# Data

## Official source and schema

This project uses the official
[TUM European Bike Sharing Dataset](https://github.com/TUMFTM/european-bike-sharing-dataset),
published with the 2025 *Transportation* article
[Data-Driven Insights into (E-)Bike-Sharing](https://doi.org/10.1007/s11116-025-10661-2).

The pipeline reads these upstream tables:

| Table | Fields used |
|---|---|
| `trips.csv` | bike and city IDs, start timestamp, coordinates, station IDs, battery, duration, distance |
| `cities.csv` | canonical city ID and name, timezone, country |
| `stations.csv` | station ID, city ID, station name and location |
| `bikes.csv` | bike ID and bike-type foreign key |
| `bike_types.csv` | type name, form factor, propulsion type |

The project does not extract `station_status.csv`: its 38 million availability
snapshots are not required for the trip-demand and observed-bike metrics in
scope. Source timestamps are Unix epoch seconds in UTC. Local hour and date are
derived with the timezone stored in `cities.csv`.

## Selected cities

| Analysis city | Canonical source rows |
|---|---|
| Berlin | `362 — Berlin` |
| Warszawa | `210 — Warszawa`; `812 — Warszawa - 2023` |
| Dresden | `685 — Dresden` |
| Bilbao | `532 — Bilbao` |

All preferred cities passed the documented project volume, active-day, and duration
quality thresholds. No replacement was required.

## Local layout

- `data/raw/` stores the downloaded 878 MiB archive, official sample CSV files,
  and the five extracted source tables. It is ignored by Git.
- `data/interim/` stores the candidate-city Parquet scan and the 6,839,701-row,
  226 MB selected trip subset. It is ignored by Git.
- `data/processed/` contains only compact committed profiling and analytical
  aggregates used by the notebook, figures, and dashboard.

No Git LFS objects or full upstream tables are committed.

## Reproduction

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/prepare_data.py --sample
python scripts/prepare_data.py
python scripts/run_analysis.py
```

The sample command validates the real schema and a representative join. The
full preparation downloads the archive only when absent, extracts only required
tables, scans the full trips CSV once to materialize candidate cities, profiles
the candidates, selects cities, and writes the local trip subset. Subsequent
analysis reads that subset rather than rescanning the 2.67 GB trips CSV.

## Cleaning rules

- Remove exact duplicate rows.
- Exclude records with missing or implausible timestamps from demand analysis.
- Use duration only from 60 seconds through 6 hours.
- Use distance only when positive and no more than 100 km.
- Mark distance unavailable when duration implies a speed above 60 km/h.
- Retain missing station IDs because free-floating trips are valid.
- Retain unknown bike types and report their share instead of imputing a type.

For the selected cities, no rows were removed for duplicates or timestamps.
The 5,009 out-of-range durations were kept as trips but excluded from duration
statistics. Per-city counts are stored in `data_quality.parquet`.

## License and citation

The source dataset and derived data are distributed under
[Creative Commons Attribution-NonCommercial 4.0 International](https://creativecommons.org/licenses/by-nc/4.0/).
The repository's MIT license applies only to project code and documentation.
Users reproducing or adapting the analysis should cite the upstream repository
and its associated paper.
