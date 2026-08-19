-- Flyber MVP launch analysis queries (PostgreSQL/PostGIS dialect)
-- Source tables match the attached taxi-rides.sql and user-research.sql files.
-- The classroom taxi SQL contains only about one tenth of the full CSV, so use
-- the full CSV/Tableau extract for final numeric results.

-- Historical fare proxy used throughout the project:
-- $2.50 initial + $0.50 MTA + $0.30 improvement surcharge, then either
-- $2.50/mile above 12 mph or $0.50/minute at or below 12 mph.
-- Passenger count has coefficient zero because a standard meter does not add a
-- per-passenger charge. Tolls, tips, and special surcharges are excluded.

WITH enriched AS (
    SELECT
        t.*,
        duration / 60.0 AS duration_minutes,
        duration / 60.0 / NULLIF(distance, 0) AS duration_distance_ratio,
        distance / NULLIF(duration / 3600.0, 0) AS speed_mph,
        3.30 + CASE
            WHEN distance / NULLIF(duration / 3600.0, 0) > 12
                THEN 2.50 * distance
            ELSE 0.50 * (duration / 60.0)
        END + 0 * passenger_count AS price_proxy,
        CASE WHEN
            duration BETWEEN 60 AND 7200
            AND distance BETWEEN 0.25 AND 50
            AND passenger_count BETWEEN 1 AND 6
            AND distance / NULLIF(duration / 3600.0, 0) BETWEEN 1 AND 80
            AND pickup_longitude BETWEEN -75 AND -72
            AND dropoff_longitude BETWEEN -75 AND -72
            AND pickup_latitude BETWEEN 39.5 AND 42
            AND dropoff_latitude BETWEEN 39.5 AND 42
            AND dropoff_datetime >= pickup_datetime
        THEN TRUE ELSE FALSE END AS analysis_valid
    FROM taxi_rides AS t
)
SELECT * FROM enriched LIMIT 100;

-- Dataset scope and primary-key verification.
SELECT
    COUNT(*) AS records,
    COUNT(DISTINCT id) AS unique_ids,
    MIN(pickup_datetime) AS pickup_start,
    MAX(pickup_datetime) AS pickup_end,
    MIN(pickup_longitude) AS min_pickup_longitude,
    MAX(pickup_longitude) AS max_pickup_longitude,
    MIN(pickup_latitude) AS min_pickup_latitude,
    MAX(pickup_latitude) AS max_pickup_latitude
FROM taxi_rides;

-- Descriptive statistics for the operational-quality subset.
WITH enriched AS (
    SELECT
        *,
        duration / 60.0 / NULLIF(distance, 0) AS ratio,
        3.30 + CASE
            WHEN distance / NULLIF(duration / 3600.0, 0) > 12 THEN 2.50 * distance
            ELSE 0.50 * (duration / 60.0)
        END + 0 * passenger_count AS price
    FROM taxi_rides
    WHERE duration BETWEEN 60 AND 7200
      AND distance BETWEEN 0.25 AND 50
      AND passenger_count BETWEEN 1 AND 6
      AND distance / NULLIF(duration / 3600.0, 0) BETWEEN 1 AND 80
      AND pickup_longitude BETWEEN -75 AND -72
      AND dropoff_longitude BETWEEN -75 AND -72
      AND pickup_latitude BETWEEN 39.5 AND 42
      AND dropoff_latitude BETWEEN 39.5 AND 42
      AND dropoff_datetime >= pickup_datetime
), measures AS (
    SELECT 'duration_seconds' AS measure, duration::numeric AS value FROM enriched
    UNION ALL SELECT 'distance_miles', distance FROM enriched
    UNION ALL SELECT 'passenger_count', passenger_count FROM enriched
    UNION ALL SELECT 'duration_distance_min_per_mile', ratio FROM enriched
    UNION ALL SELECT 'price_proxy_usd', price FROM enriched
), stats AS (
    SELECT
        measure,
        COUNT(*) AS n,
        AVG(value) AS mean,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY value) AS median,
        STDDEV_SAMP(value) AS sd
    FROM measures
    GROUP BY measure
)
SELECT
    *,
    mean - sd AS mean_minus_1sd,
    mean + sd AS mean_plus_1sd,
    mean - 2 * sd AS mean_minus_2sd,
    mean + 2 * sd AS mean_plus_2sd
FROM stats
ORDER BY measure;

-- Passenger-count histogram.
SELECT passenger_count, COUNT(*) AS rides
FROM taxi_rides
WHERE passenger_count BETWEEN 1 AND 6
GROUP BY passenger_count
ORDER BY passenger_count;

-- Temporal demand.
SELECT EXTRACT(HOUR FROM pickup_datetime)::int AS pickup_hour, COUNT(*) AS rides
FROM taxi_rides GROUP BY 1 ORDER BY 1;

SELECT TO_CHAR(pickup_datetime, 'FMDay') AS pickup_day, COUNT(*) AS rides
FROM taxi_rides GROUP BY 1 ORDER BY rides DESC;

SELECT DATE_TRUNC('month', pickup_datetime) AS pickup_month, COUNT(*) AS rides
FROM taxi_rides GROUP BY 1 ORDER BY 1;

-- Optional PostGIS spatial join. Load the NYC NTA GeoJSON into a table named
-- nyc_nta(nta2020, ntaname, boroname, shape_area, geom geometry).
WITH endpoints AS (
    SELECT
        t.id,
        t.duration / 60.0 / NULLIF(t.distance, 0) AS ratio,
        ST_SetSRID(ST_MakePoint(t.pickup_longitude, t.pickup_latitude), 4326) AS pickup_geom,
        ST_SetSRID(ST_MakePoint(t.dropoff_longitude, t.dropoff_latitude), 4326) AS dropoff_geom
    FROM taxi_rides AS t
    WHERE t.duration BETWEEN 60 AND 7200
      AND t.distance BETWEEN 0.25 AND 50
      AND t.passenger_count BETWEEN 1 AND 6
      AND t.distance / NULLIF(t.duration / 3600.0, 0) BETWEEN 1 AND 80
)
SELECT
    n.ntaname,
    n.boroname,
    COUNT(*) AS pickup_rides,
    COUNT(*) / NULLIF(n.shape_area / 27878400.0, 0) AS pickups_per_square_mile,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY e.ratio) AS median_minutes_per_mile
FROM endpoints AS e
JOIN nyc_nta AS n ON ST_Contains(n.geom, e.pickup_geom)
GROUP BY n.nta2020, n.ntaname, n.boroname, n.shape_area
HAVING COUNT(*) >= 1000
ORDER BY pickups_per_square_mile DESC;

-- Survey adoption and willingness to pay.
SELECT
    COUNT(*) FILTER (WHERE q8 IS NOT NULL) AS valid_answers,
    COUNT(*) FILTER (WHERE q8 = 'Y') AS willing,
    AVG((q8 = 'Y')::int::numeric) FILTER (WHERE q8 IS NOT NULL) AS willing_share,
    AVG(q9) FILTER (WHERE q8 = 'Y') AS mean_willing_price,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY q9) FILTER (WHERE q8 = 'Y') AS median_willing_price
FROM user_research;

SELECT q4 AS income_band, COUNT(*) AS respondents,
       AVG((q8 = 'Y')::int::numeric) AS willing_share,
       AVG(q9) FILTER (WHERE q8 = 'Y') AS mean_willing_price
FROM user_research
WHERE q8 IS NOT NULL
GROUP BY q4
ORDER BY q4;

SELECT q10 AS objection, COUNT(*) AS respondents
FROM user_research
WHERE q8 = 'N'
GROUP BY q10
ORDER BY respondents DESC;
