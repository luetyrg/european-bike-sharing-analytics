# Data

## Official source

This project uses the
[TUM European Bike Sharing Dataset](https://github.com/TUMFTM/european-bike-sharing-dataset).
Its relational CSV export contains `trips`, `cities`, `stations`, `bikes`, and
`bike_types`, which are the source tables used here. Timestamps are Unix epoch
seconds in UTC and are converted using the IANA timezone stored in `cities`.

The upstream dataset is distributed under
[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). That license
applies to the source data and derived data subsets. The MIT license in this
repository applies only to project code and documentation.

## Local layout

- `data/raw/` holds the downloaded upstream archive and extracted CSV files.
  It is ignored by Git because the complete dataset is large.
- `data/interim/` holds temporary profiling and filtered data. It is ignored.
- `data/processed/` holds compact analytical tables required by the notebook,
  figures, and dashboard.

Run `python scripts/prepare_data.py` to download the official archive when it
is absent, profile candidate cities, clean the selected trips, and build the
Parquet subset. Run `python scripts/run_analysis.py` to produce the committed
aggregates and figures.

