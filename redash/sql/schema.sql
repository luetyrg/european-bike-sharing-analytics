-- Dedicated schema within the new bike-redash instance, separate from app metadata.
CREATE SCHEMA IF NOT EXISTS bike;
CREATE TABLE IF NOT EXISTS bike.demand_hourly (
 city text NOT NULL, trip_date date NOT NULL, hour smallint NOT NULL CHECK(hour BETWEEN 0 AND 23),
 trips bigint NOT NULL, valid_duration_trips bigint NOT NULL, duration_sum_min double precision NOT NULL,
 valid_distance_trips bigint NOT NULL, distance_sum_km double precision NOT NULL,
 known_starts bigint NOT NULL,known_ends bigint NOT NULL,station_pair_trips bigint NOT NULL,
 PRIMARY KEY(city,trip_date,hour)
);
CREATE TABLE IF NOT EXISTS bike.station_daily (
 city text NOT NULL,trip_date date NOT NULL,station_id bigint NOT NULL,station_name text NOT NULL,
 starts bigint NOT NULL,ends bigint NOT NULL,PRIMARY KEY(city,trip_date,station_id)
);
CREATE TABLE IF NOT EXISTS bike.city_coverage (
 city text PRIMARY KEY,first_date date,last_date date,active_days integer,trips bigint,
 valid_duration_trips bigint,mean_duration_min double precision,median_duration_min double precision,
 known_starts bigint,known_ends bigint,station_pair_trips bigint
);
BEGIN;
TRUNCATE bike.demand_hourly,bike.station_daily,bike.city_coverage;
COPY bike.demand_hourly FROM '/import/demand_hourly.csv' WITH (FORMAT csv,HEADER true);
COPY bike.station_daily FROM '/import/station_daily.csv' WITH (FORMAT csv,HEADER true);
COPY bike.city_coverage FROM '/import/city_coverage.csv' WITH (FORMAT csv,HEADER true);
COMMIT;
ANALYZE bike.demand_hourly;
ANALYZE bike.station_daily;
ANALYZE bike.city_coverage;
