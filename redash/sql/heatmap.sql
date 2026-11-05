-- Denominator: observed dates of each weekday, not dates with a trip in that hour.
WITH f AS (
 SELECT *,extract(isodow FROM trip_date)::integer AS dow FROM bike.demand_hourly
 WHERE city='{{ city }}' AND trip_date BETWEEN '{{ period.start }}'::date AND '{{ period.end }}'::date
), days AS (SELECT dow,count(DISTINCT trip_date) AS days FROM f GROUP BY dow),
 counts AS (SELECT dow,hour,sum(trips) AS trips FROM f GROUP BY dow,hour)
SELECT h AS hour,
 CASE d WHEN 1 THEN '1 Пн' WHEN 2 THEN '2 Вт' WHEN 3 THEN '3 Ср' WHEN 4 THEN '4 Чт'
 WHEN 5 THEN '5 Пт' WHEN 6 THEN '6 Сб' ELSE '7 Вс' END AS weekday,
 round(coalesce(c.trips,0)::numeric/nullif(days.days,0),2) AS trips_per_observed_day
FROM generate_series(1,7) d CROSS JOIN generate_series(0,23) h
LEFT JOIN counts c ON c.dow=d AND c.hour=h LEFT JOIN days ON days.dow=d
ORDER BY d,h;
