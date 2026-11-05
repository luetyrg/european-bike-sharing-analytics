-- No observations => NULL, not an invented zero-demand day.
WITH daily AS (
 SELECT trip_date,sum(trips) AS trips FROM bike.demand_hourly
 WHERE city='{{ city }}' AND trip_date BETWEEN '{{ period.start }}'::date AND '{{ period.end }}'::date
 GROUP BY trip_date
)
SELECT d::date AS date,daily.trips
FROM generate_series('{{ period.start }}'::date,'{{ period.end }}'::date,'1 day') d
LEFT JOIN daily ON daily.trip_date=d::date ORDER BY date;
