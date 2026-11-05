"""Read the existing cleaned project subset; build additive, date-filterable marts."""
import argparse
import hashlib
import json
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True, help='Original project root (read-only)')
    args = parser.parse_args()
    source = args.source / 'data/interim/trips_selected.parquet'
    out = ROOT / 'data'
    out.mkdir(exist_ok=True)
    c = duckdb.connect()
    c.execute('SET threads=4')
    source_sql = source.as_posix().replace("'", "''")
    c.execute(f"CREATE VIEW trips AS SELECT * FROM read_parquet('{source_sql}')")
    queries = {
        'demand_hourly': '''SELECT city, trip_date, hour,
            count(*) AS trips, count(duration_min) AS valid_duration_trips,
            coalesce(sum(duration_min),0) AS duration_sum_min,
            count(distance_km) AS valid_distance_trips,
            coalesce(sum(distance_km),0) AS distance_sum_km,
            count(*) FILTER (WHERE start_station_id IS NOT NULL) AS known_starts,
            count(*) FILTER (WHERE end_station_id IS NOT NULL) AS known_ends,
            count(*) FILTER (WHERE has_station_pair) AS station_pair_trips
            FROM trips GROUP BY city,trip_date,hour ORDER BY city,trip_date,hour''',
        'station_daily': '''WITH events AS (
            SELECT city,trip_date,start_station_id AS station_id,start_station_name AS station_name,
                   1 AS starts,0 AS ends FROM trips WHERE start_station_id IS NOT NULL
            UNION ALL
            SELECT city,trip_date,end_station_id,end_station_name,0,1
            FROM trips WHERE end_station_id IS NOT NULL)
            SELECT city,trip_date,station_id,
                   coalesce(max(station_name),'Station ' || station_id::VARCHAR) AS station_name,
                   sum(starts) AS starts,sum(ends) AS ends
            FROM events GROUP BY city,trip_date,station_id ORDER BY city,trip_date,station_id''',
        'city_coverage': '''SELECT city,min(trip_date) AS first_date,max(trip_date) AS last_date,
            count(DISTINCT trip_date) AS active_days,count(*) AS trips,
            count(duration_min) AS valid_duration_trips,
            avg(duration_min) AS mean_duration_min,
            median(duration_min) AS median_duration_min,
            count(*) FILTER (WHERE start_station_id IS NOT NULL) AS known_starts,
            count(*) FILTER (WHERE end_station_id IS NOT NULL) AS known_ends,
            count(*) FILTER (WHERE has_station_pair) AS station_pair_trips
            FROM trips GROUP BY city ORDER BY city'''
    }
    manifest = {'source_file': source.name, 'source_sha256': hashlib.file_digest(source.open('rb'),'sha256').hexdigest(), 'marts': {}}
    for name, sql in queries.items():
        c.execute(f'CREATE TEMP TABLE {name} AS {sql}')
        dest = (out / f'{name}.csv').as_posix().replace("'", "''")
        c.execute(f"COPY {name} TO '{dest}' (HEADER, FORMAT CSV)")
        parquet=(out/f'{name}.parquet').as_posix().replace("'", "''")
        c.execute(f"COPY {name} TO '{parquet}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        manifest['marts'][name] = c.execute(f'SELECT count(*) FROM {name}').fetchone()[0]
    total = c.execute('SELECT count(*) FROM trips').fetchone()[0]
    assert c.execute('SELECT sum(trips) FROM demand_hourly').fetchone()[0] == total
    starts, ends = c.execute('SELECT sum(starts),sum(ends) FROM station_daily').fetchone()
    assert (starts,ends) == c.execute('SELECT sum(known_starts),sum(known_ends) FROM demand_hourly').fetchone()
    assert c.execute('SELECT count(*) FROM station_daily WHERE starts<0 OR ends<0').fetchone()[0] == 0
    manifest['total_trips'] = total
    manifest['cities'] = c.execute('SELECT * FROM city_coverage').fetchdf().to_dict('records')
    manifest['validation'] = {'trip_counts_reconciled': True,'station_events_reconciled': True}
    (ROOT/'data_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False,default=str),encoding='utf-8')
    print(json.dumps({k:v for k,v in manifest.items() if k!='cities'},indent=2))

if __name__ == '__main__': main()
