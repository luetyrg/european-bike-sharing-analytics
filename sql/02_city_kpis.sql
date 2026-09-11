-- Purpose: compare a compact, normalized set of city KPIs.
WITH base AS (
    SELECT
        city,
        COUNT(*) AS total_trips,
        COUNT(DISTINCT trip_date) AS active_days,
        COUNT(DISTINCT bike_id) AS unique_bikes,
        MEDIAN(duration_min) AS median_duration_min,
        MEDIAN(distance_km) AS median_distance_km,
        AVG(is_weekend::INTEGER) AS weekend_share
    FROM trips
    GROUP BY city
),
hourly AS (
    SELECT city, hour, COUNT(*) AS trips
    FROM trips
    GROUP BY city, hour
),
ranked_hours AS (
    SELECT
        city,
        hour,
        trips,
        ROW_NUMBER() OVER (PARTITION BY city ORDER BY trips DESC, hour) AS rank
    FROM hourly
)
SELECT
    b.city,
    b.total_trips,
    b.active_days,
    b.total_trips / NULLIF(b.active_days, 0)::DOUBLE AS trips_per_active_day,
    p.stations,
    b.unique_bikes,
    b.median_duration_min,
    b.median_distance_km,
    b.weekend_share,
    h.hour AS peak_hour,
    b.total_trips / NULLIF(b.unique_bikes * b.active_days, 0)::DOUBLE
        AS fleet_utilization_proxy
FROM base b
LEFT JOIN city_profile p USING (city)
LEFT JOIN ranked_hours h ON b.city = h.city AND h.rank = 1
ORDER BY trips_per_active_day DESC;

