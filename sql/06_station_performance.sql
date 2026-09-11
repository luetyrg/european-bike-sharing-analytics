-- Purpose: identify the most active observed stations as starts and destinations.
WITH station_events AS (
    SELECT city, start_station_id AS station_id, start_station_name AS station_name,
           1 AS starts, 0 AS ends
    FROM trips
    WHERE start_station_id IS NOT NULL
    UNION ALL
    SELECT city, end_station_id AS station_id, end_station_name AS station_name,
           0 AS starts, 1 AS ends
    FROM trips
    WHERE end_station_id IS NOT NULL
),
summed AS (
    SELECT
        city,
        station_id,
        COALESCE(MAX(station_name), 'Station ' || CAST(station_id AS VARCHAR)) AS station_name,
        SUM(starts) AS trip_starts,
        SUM(ends) AS trip_ends,
        SUM(starts + ends) AS total_activity
    FROM station_events
    GROUP BY city, station_id
),
ranked AS (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY city ORDER BY total_activity DESC, station_id
    ) AS city_rank
    FROM summed
)
SELECT *
FROM ranked
WHERE city_rank <= 10
ORDER BY city, city_rank;
