-- Purpose: confirm the observation period and key-field coverage by selected city.
SELECT
    city,
    COUNT(*) AS trips,
    MIN(trip_date) AS observation_start,
    MAX(trip_date) AS observation_end,
    COUNT(DISTINCT trip_date) AS active_days,
    COUNT(DISTINCT bike_id) AS unique_bikes,
    COUNT(DISTINCT start_station_id) AS observed_start_stations,
    COUNT(DISTINCT end_station_id) AS observed_end_stations,
    AVG((duration_min IS NOT NULL)::INTEGER) AS valid_duration_share,
    AVG((distance_km IS NOT NULL)::INTEGER) AS valid_distance_share,
    AVG(has_station_pair::INTEGER) AS station_pair_share,
    AVG((propulsion_type <> 'unknown')::INTEGER) AS known_bike_type_share
FROM trips
GROUP BY city
ORDER BY trips DESC;

