-- Purpose: compare local-time demand profiles without bias from unequal coverage.
WITH hourly AS (
    SELECT city, hour, COUNT(*) AS trips
    FROM trips
    GROUP BY city, hour
),
city_totals AS (
    SELECT city, COUNT(*) AS city_trips, COUNT(DISTINCT trip_date) AS active_days
    FROM trips
    GROUP BY city
)
SELECT
    h.city,
    h.hour,
    h.trips,
    h.trips / NULLIF(t.city_trips, 0)::DOUBLE AS trip_share,
    h.trips / NULLIF(t.active_days, 0)::DOUBLE AS trips_per_active_day
FROM hourly h
JOIN city_totals t USING (city)
ORDER BY h.city, h.hour;

