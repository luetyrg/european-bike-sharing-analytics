-- Cohort of trips starting in the selected dates; not end-time stock accounting.
SELECT station_id AS "ID",max(station_name) AS "Станция",sum(starts) AS "Выдачи",
 sum(ends) AS "Возвраты",sum(starts)-sum(ends) AS "Выдачи − возвраты",
 round(100.0*(sum(starts)-sum(ends))/nullif(sum(starts)+sum(ends),0),1) AS "Дисбаланс, %"
FROM bike.station_daily WHERE city='{{ city }}'
AND trip_date BETWEEN '{{ period.start }}'::date AND '{{ period.end }}'::date
GROUP BY station_id ORDER BY abs(sum(starts)-sum(ends)) DESC,station_id LIMIT 15;
