-- Purpose: summarize valid duration and distance distributions robustly.
SELECT
    city,
    COUNT(*) AS trips,
    COUNT(duration_min) AS trips_with_valid_duration,
    MEDIAN(duration_min) AS median_duration_min,
    QUANTILE_CONT(duration_min, 0.25) AS duration_p25_min,
    QUANTILE_CONT(duration_min, 0.75) AS duration_p75_min,
    COUNT(distance_km) AS trips_with_valid_distance,
    MEDIAN(distance_km) AS median_distance_km,
    QUANTILE_CONT(distance_km, 0.25) AS distance_p25_km,
    QUANTILE_CONT(distance_km, 0.75) AS distance_p75_km
FROM trips
GROUP BY city
ORDER BY city;

