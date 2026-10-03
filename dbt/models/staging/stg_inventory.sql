-- Staging model for daily warehouse inventory levels
WITH source AS (
    SELECT * FROM {{ source('raw_wms', 'inventory_snapshots') }}
),

renamed AS (
    SELECT
        snapshot_id AS inventory_id,
        CAST(snapshot_date AS DATE) AS snapshot_date,
        CAST(product_id AS INTEGER) AS product_key,
        CAST(warehouse_region_id AS INTEGER) AS region_key,
        CAST(stock_level AS INTEGER) AS stock_on_hand,
        CAST(daily_burn_rate AS DOUBLE PRECISION) AS burn_rate,
        CAST(stock_level / NULLIF(daily_burn_rate, 0) AS DOUBLE PRECISION) AS days_of_supply,
        _snapshot_timestamp
    FROM source
)

SELECT * FROM renamed
