-- Purpose: contrast observed weekday and weekend demand using normalized rates.
WITH grouped AS (
    SELECT
        city,
        CASE WHEN is_weekend THEN 'Weekend' ELSE 'Weekday' END AS day_type,
        COUNT(*) AS trips,
        COUNT(DISTINCT trip_date) AS active_days
    FROM trips
    GROUP BY city, day_type
),
totals AS (
    SELECT city, SUM(trips) AS city_trips
    FROM grouped
    GROUP BY city
)
SELECT
    g.city,
    g.day_type,
    g.trips,
    g.active_days,
    g.trips / NULLIF(g.active_days, 0)::DOUBLE AS trips_per_active_day,
    g.trips / NULLIF(t.city_trips, 0)::DOUBLE AS trip_share
FROM grouped g
JOIN totals t USING (city)
ORDER BY g.city, g.day_type;

