-- Purpose: rank station-to-station pairs where both endpoints are observed.
WITH routes AS (
    SELECT
        city,
        start_station_id,
        COALESCE(start_station_name, 'Unknown station') AS start_station_name,
        end_station_id,
        COALESCE(end_station_name, 'Unknown station') AS end_station_name,
        COUNT(*) AS trips
    FROM trips
    WHERE start_station_id IS NOT NULL
      AND end_station_id IS NOT NULL
      AND start_station_id <> end_station_id
    GROUP BY ALL
),
ranked AS (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY city ORDER BY trips DESC, start_station_id, end_station_id
    ) AS city_rank
    FROM routes
)
SELECT *
FROM ranked
WHERE city_rank <= 10
ORDER BY city, city_rank;

