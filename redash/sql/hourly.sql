WITH filtered AS (
 SELECT * FROM bike.demand_hourly WHERE city='{{ city }}'
 AND trip_date BETWEEN '{{ period.start }}'::date AND '{{ period.end }}'::date
), totals AS (SELECT count(DISTINCT trip_date) AS days FROM filtered)
SELECT h AS hour,round(coalesce(sum(f.trips),0)::numeric/nullif((SELECT days FROM totals),0),2) AS trips_per_active_day
FROM generate_series(0,23) h LEFT JOIN filtered f ON f.hour=h
GROUP BY h ORDER BY h;
