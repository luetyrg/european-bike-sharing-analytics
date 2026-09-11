-- Purpose: compare trips per observed bike and the distribution across each fleet.
WITH bike_activity AS (
    SELECT
        city,
        bike_id,
        COUNT(*) AS trips,
        COUNT(DISTINCT trip_date) AS bike_active_days
    FROM trips
    WHERE bike_id IS NOT NULL
    GROUP BY city, bike_id
),
city_days AS (
    SELECT city, COUNT(DISTINCT trip_date) AS city_active_days
    FROM trips
    GROUP BY city
)
SELECT
    b.city,
    COUNT(*) AS observed_bikes,
    SUM(b.trips) AS trips_with_bike_id,
    MEDIAN(b.trips) AS median_trips_per_bike,
    QUANTILE_CONT(b.trips, 0.75) AS trips_per_bike_p75,
    AVG(b.bike_active_days) AS avg_active_days_per_bike,
    SUM(b.trips) / NULLIF(COUNT(*) * d.city_active_days, 0)::DOUBLE
        AS fleet_utilization_proxy
FROM bike_activity b
JOIN city_days d USING (city)
GROUP BY b.city, d.city_active_days
ORDER BY fleet_utilization_proxy DESC;

