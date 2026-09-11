-- Purpose: compare observed human-powered and electric bike trip patterns.
WITH grouped AS (
    SELECT
        city,
        propulsion_type,
        COUNT(*) AS trips,
        COUNT(DISTINCT bike_id) AS unique_bikes,
        MEDIAN(duration_min) AS median_duration_min,
        MEDIAN(distance_km) AS median_distance_km
    FROM trips
    GROUP BY city, propulsion_type
),
totals AS (
    SELECT city, SUM(trips) AS city_trips
    FROM grouped
    GROUP BY city
)
SELECT
    g.*,
    g.trips / NULLIF(t.city_trips, 0)::DOUBLE AS trip_share
FROM grouped g
JOIN totals t USING (city)
ORDER BY g.city, g.trips DESC;

