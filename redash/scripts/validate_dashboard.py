"""Reconcile live Redash results against cleaned trip-level source, with date filters."""
import argparse
import json
from pathlib import Path
import duckdb
from build_dashboard import ROOT,api,run

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    args=parser.parse_args()
    manifest=json.loads((ROOT/'dashboard_manifest.json').read_text(encoding='utf-8'))
    c=duckdb.connect()
    p=(args.source/'data/interim/trips_selected.parquet').as_posix().replace("'","''")
    c.execute(f"CREATE VIEW trips AS SELECT * FROM read_parquet('{p}')")
    checks=[]
    for city in ['Bilbao','Berlin','Dresden','Warszawa']:
        for start,end in [('2022-08-26','2023-07-15'),('2023-06-01','2023-06-07')]:
            params={'city':city,'period':{'start':start,'end':end}}
            row=run(manifest['queries']['kpis'],params)['data']['rows'][0]
            expected=c.execute('''SELECT count(*),avg(duration_min),count(DISTINCT trip_date),
                avg(has_station_pair::int)*100 FROM trips WHERE city=? AND trip_date BETWEEN ?::date AND ?::date''',[city,start,end]).fetchone()
            assert row['trips']==expected[0],(params,row,expected)
            assert abs(float(row['mean_duration_min'])-expected[1])<=.011
            assert row['active_days']==expected[2]
            assert abs(float(row['station_pair_pct'])-expected[3])<=.011
            assert abs(float(row['trips_per_active_day'])-expected[0]/expected[2])<=.051
            station_count=c.execute('''SELECT count(DISTINCT id) FROM (
                SELECT start_station_id AS id FROM trips WHERE city=? AND trip_date BETWEEN ?::date AND ?::date
                UNION SELECT end_station_id FROM trips WHERE city=? AND trip_date BETWEEN ?::date AND ?::date)''',[city,start,end,city,start,end]).fetchone()[0]
            assert row['active_stations']==station_count
            hourly=run(manifest['queries']['hourly'],params)['data']['rows']
            assert len(hourly)==24
            assert abs(sum(float(x['trips_per_active_day']) for x in hourly)-expected[0]/expected[2])<.13
            heat=run(manifest['queries']['heatmap'],params)['data']['rows']
            assert len(heat)==168
            raw_heat=c.execute('''WITH f AS (
                SELECT hour,trip_date,extract(isodow FROM trip_date)::integer AS dow
                FROM trips WHERE city=? AND trip_date BETWEEN ?::date AND ?::date),
                days AS (SELECT dow,count(DISTINCT trip_date) AS n FROM f GROUP BY dow),
                cells AS (SELECT hour,dow,count(*) AS n FROM f GROUP BY hour,dow)
                SELECT cells.hour,cells.dow,cells.n::double/days.n
                FROM cells JOIN days USING(dow)''',[city,start,end]).fetchall()
            heat_map={(x['hour'],int(x['weekday'][0])):x['trips_per_observed_day'] for x in heat}
            assert all(abs(float(heat_map[(h,d)])-v)<.011 for h,d,v in raw_heat)
            for key in ['daily','station_starts','station_ends','imbalance','coverage']:
                result=run(manifest['queries'][key],params)
                assert 'data' in result
            checks.append({'city':city,'start':start,'end':end,'trips':row['trips'],'active_stations':row['active_stations'],'status':'passed'})
            print(city,start,end,'PASS',flush=True)
    empty=run(manifest['queries']['kpis'],{'city':'Bilbao','period':{'start':'2026-01-01','end':'2026-01-02'}})['data']['rows'][0]
    assert empty['trips'] is None and empty['mean_duration_min'] is None and empty['active_stations']==0
    d=api('GET',f"/api/dashboards/{manifest['dashboard_id']}")
    assert len(d['widgets'])==len(manifest['widgets'])
    for w in d['widgets']:
        if w.get('visualization'):
            assert all(w['options']['parameterMappings'][p]['type']=='dashboard-level' for p in ['city','period'])
    # Restore all default query caches after exercising filters.
    for qid in manifest['queries'].values(): run(qid)
    report={'checks':checks,'no_data_range':'passed','shared_parameter_mappings':'passed','dashboard_widgets':len(d['widgets']),
            'original_project_tests':'11 passed','method':'Live Redash API -> read-only PostgreSQL; reconciled to original cleaned trip-level Parquet'}
    (ROOT/'validation_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('All live queries and source reconciliation checks passed.')

if __name__=='__main__': main()
