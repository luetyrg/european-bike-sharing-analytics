WITH grouped AS (
SELECT station_id,max(station_name) AS station_name,sum(starts) AS starts
FROM bike.station_daily WHERE city='{{ city }}'
AND trip_date BETWEEN '{{ period.start }}'::date AND '{{ period.end }}'::date
GROUP BY station_id
)
SELECT CASE WHEN count(*) OVER(PARTITION BY station_name)>1
 THEN station_name || ' · ' || station_id ELSE station_name END AS station,starts
FROM grouped ORDER BY starts DESC,station_id LIMIT 10;
