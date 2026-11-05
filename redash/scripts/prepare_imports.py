"""Convert the committed Parquet marts into PostgreSQL COPY inputs."""
import json
from pathlib import Path
import duckdb

ROOT=Path(__file__).resolve().parents[1]
MARTS=('demand_hourly','station_daily','city_coverage')

def main():
    manifest=json.loads((ROOT/'data_manifest.json').read_text(encoding='utf-8'))
    c=duckdb.connect()
    for name in MARTS:
        parquet=ROOT/'data'/f'{name}.parquet'
        source=parquet.as_posix().replace("'","''")
        assert parquet.exists(),f'Missing bundled mart: {parquet.name}'
        count=c.execute(f"SELECT count(*) FROM read_parquet('{source}')").fetchone()[0]
        assert count==manifest['marts'][name],f'Unexpected row count: {name}'
        temporary=ROOT/'data'/f'{name}.tmp'
        target=temporary.as_posix().replace("'","''")
        c.execute(f"COPY (SELECT * FROM read_parquet('{source}')) TO '{target}' (FORMAT CSV,HEADER)")
        temporary.replace(ROOT/'data'/f'{name}.csv')
        print(f'{name}: {count:,} rows ready for PostgreSQL COPY')
    total=c.execute(f"SELECT sum(trips) FROM read_parquet('{(ROOT/'data/demand_hourly.parquet').as_posix()}')").fetchone()[0]
    assert total==manifest['total_trips']

if __name__=='__main__': main()
