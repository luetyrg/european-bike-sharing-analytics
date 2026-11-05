-- Weighted means; counts use every retained trip, including invalid durations.
WITH filtered AS (
 SELECT * FROM bike.demand_hourly
 WHERE city='{{ city }}' AND trip_date BETWEEN '{{ period.start }}'::date AND '{{ period.end }}'::date
), stations AS (
 SELECT count(DISTINCT station_id) AS active_stations FROM bike.station_daily
 WHERE city='{{ city }}' AND trip_date BETWEEN '{{ period.start }}'::date AND '{{ period.end }}'::date
)
SELECT sum(trips) AS trips,
 round((sum(duration_sum_min)/nullif(sum(valid_duration_trips),0))::numeric,2) AS mean_duration_min,
 (SELECT active_stations FROM stations) AS active_stations,
 round(sum(trips)::numeric/nullif(count(DISTINCT trip_date),0),1) AS trips_per_active_day,
 round(100.0*sum(station_pair_trips)/nullif(sum(trips),0),2) AS station_pair_pct,
 round(100.0*sum(valid_duration_trips)/nullif(sum(trips),0),2) AS valid_duration_pct,
 count(DISTINCT trip_date) AS active_days
FROM filtered;
