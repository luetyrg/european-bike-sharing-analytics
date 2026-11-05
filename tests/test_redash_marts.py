"""Check the published BI data without requiring Docker or the large raw dataset."""
import json
from pathlib import Path
import duckdb

ROOT=Path(__file__).resolve().parents[1]/'redash'

def connect():
    c=duckdb.connect()
    for name in ['demand_hourly','station_daily','city_coverage']:
        path=(ROOT/'data'/f'{name}.parquet').as_posix().replace("'","''")
        c.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{path}')")
    return c

def test_bundled_bi_marts_have_expected_rows_and_unique_keys():
    manifest=json.loads((ROOT/'data_manifest.json').read_text(encoding='utf-8'))
    with connect() as c:
        for name,count in manifest['marts'].items():
            assert c.execute(f'SELECT count(*) FROM {name}').fetchone()[0]==count
        assert c.execute('SELECT count(*)=count(DISTINCT (city,trip_date,hour)) FROM demand_hourly').fetchone()[0]
        assert c.execute('SELECT count(*)=count(DISTINCT (city,trip_date,station_id)) FROM station_daily').fetchone()[0]
        assert c.execute('SELECT sum(trips) FROM demand_hourly').fetchone()[0]==6_839_701

def test_demand_characteristics_and_station_coverage_remain_consistent():
    with connect() as c:
        invalid=c.execute('''SELECT count(*) FROM demand_hourly WHERE
            hour NOT BETWEEN 0 AND 23 OR trips<=0 OR valid_duration_trips<0
            OR valid_duration_trips>trips OR duration_sum_min<valid_duration_trips
            OR duration_sum_min>360*valid_duration_trips
            OR station_pair_trips>known_starts OR station_pair_trips>known_ends
            OR known_starts>trips OR known_ends>trips''').fetchone()[0]
        assert invalid==0
        assert c.execute('SELECT sum(trips-valid_duration_trips) FROM demand_hourly').fetchone()[0]==5_009

def test_station_events_reconcile_with_demand_for_each_city():
    with connect() as c:
        rows=c.execute('''WITH demand AS (
            SELECT city,sum(known_starts) AS starts,sum(known_ends) AS ends
            FROM demand_hourly GROUP BY city), stations AS (
            SELECT city,sum(starts) AS starts,sum(ends) AS ends
            FROM station_daily GROUP BY city)
            SELECT d.city,d.starts=s.starts,d.ends=s.ends FROM demand d JOIN stations s USING(city)''').fetchall()
        assert {r[0] for r in rows}=={'Berlin','Bilbao','Dresden','Warszawa'}
        assert all(starts and ends for _,starts,ends in rows)
