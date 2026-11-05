WITH grouped AS (
SELECT station_id,max(station_name) AS station_name,sum(ends) AS ends
FROM bike.station_daily WHERE city='{{ city }}'
AND trip_date BETWEEN '{{ period.start }}'::date AND '{{ period.end }}'::date
GROUP BY station_id
)
SELECT CASE WHEN count(*) OVER(PARTITION BY station_name)>1
 THEN station_name || ' · ' || station_id ELSE station_name END AS station,ends
FROM grouped ORDER BY ends DESC,station_id LIMIT 10;
