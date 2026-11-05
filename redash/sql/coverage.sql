WITH f AS (
 SELECT * FROM bike.demand_hourly WHERE city='{{ city }}'
 AND trip_date BETWEEN '{{ period.start }}'::date AND '{{ period.end }}'::date
)
SELECT c.city AS "Город",c.first_date AS "Первое наблюдение",c.last_date AS "Последнее наблюдение",
 count(DISTINCT f.trip_date) AS "Активных дней в фильтре",
 round(100.0*sum(f.known_starts)/nullif(sum(f.trips),0),2) AS "Известна станция выдачи, %",
 round(100.0*sum(f.known_ends)/nullif(sum(f.trips),0),2) AS "Известна станция возврата, %",
 round(100.0*sum(f.station_pair_trips)/nullif(sum(f.trips),0),2) AS "Известны обе станции, %"
FROM bike.city_coverage c LEFT JOIN f ON c.city=f.city WHERE c.city='{{ city }}'
GROUP BY c.city,c.first_date,c.last_date;
